import logging
import uuid
from datetime import timedelta
from urllib.parse import quote

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import PortReservation, SandboxSession

logger = logging.getLogger(__name__)


def _docker_api(path, method="post", data=None, timeout=None):
    """Make an authenticated call to Docker's Remote API."""
    cert_dir = settings.DOCKER_TLS_CERT_PATH
    kwargs = {
        "headers": {"Content-Type": "application/json"},
        "timeout": timeout or settings.DOCKER_API_TIMEOUT,
    }
    if settings.DOCKER_TLS_VERIFY:
        kwargs["verify"] = f"{cert_dir}/{settings.DOCKER_TLS_CA_FILE}"
        kwargs["cert"] = (
            f"{cert_dir}/{settings.DOCKER_TLS_CERT_FILE}",
            f"{cert_dir}/{settings.DOCKER_TLS_KEY_FILE}",
        )
    if data is not None:
        kwargs["json"] = data
    try:
        response = requests.request(method, f"{settings.DOCKER_HOST}{path}", **kwargs)
        response.raise_for_status()
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            # Docker image pulls return newline-delimited progress JSON, not one JSON value.
            return {}
    except (requests.RequestException, OSError) as exc:
        logger.error("Docker API %s %s failed: %s", method.upper(), path, exc)
        return None


def _ensure_image(image):
    encoded = quote(image, safe="")
    if _docker_api(f"/images/{encoded}/json", method="get") is not None:
        return True
    logger.info("Pulling Docker image %s", image)
    # Image pulls return an NDJSON progress stream; a successful HTTP response is enough,
    # then verify the image is available locally.
    if _docker_api(f"/images/create?fromImage={encoded}", method="post", timeout=300) is None:
        return False
    return _docker_api(f"/images/{encoded}/json", method="get") is not None


def _create_network():
    name = f"somacloud-{uuid.uuid4().hex[:12]}"
    result = _docker_api("/networks/create", data={"Name": name, "Driver": "bridge", "Labels": {"somacloud.managed": "true"}})
    return name if result and result.get("Id") else None


def _remove_network(name):
    if name:
        _docker_api(f"/networks/{quote(name, safe='')}", method="delete")


def _docker_used_ports():
    containers = _docker_api("/containers/json?all=1", method="get") or []
    return {
        port.get("PublicPort")
        for container in containers
        for port in container.get("Ports", [])
        if port.get("PublicPort")
    }


def _reserve_ports(session, count):
    """Atomically reserve ports in the configured range for one sandbox."""
    unavailable = _docker_used_ports()
    reserved = []
    for port in range(settings.DOCKER_PORT_START, settings.DOCKER_PORT_END + 1):
        if port in unavailable:
            continue
        try:
            with transaction.atomic():
                PortReservation.objects.create(port=port, session=session)
            reserved.append(port)
            if len(reserved) == count:
                return reserved
        except IntegrityError:
            continue
    PortReservation.objects.filter(session=session).delete()
    return []


def _release_ports(session):
    PortReservation.objects.filter(session=session).delete()


def _resources(profile, network, port, container_port):
    port_key = f"{container_port}/tcp"
    return {
        "NetworkMode": network,
        "Memory": int(profile.memory_mb * 1024 * 1024),
        "MemorySwap": int(profile.memory_mb * 1024 * 1024),
        "NanoCpus": int(profile.cpu_count * 1_000_000_000),
        "PortBindings": {port_key: [{"HostPort": str(port)}]},
    }


def _create_container(image, name, network, profile, host_port, container_port, env=None, command=""):
    port_key = f"{container_port}/tcp"
    config = {
        "Image": image,
        "Env": [f"{key}={value}" for key, value in (env or {}).items()],
        "ExposedPorts": {port_key: {}},
        "HostConfig": _resources(profile, network, host_port, container_port),
        "Labels": {"somacloud.managed": "true"},
    }
    if command:
        config["Cmd"] = command.split()
    created = _docker_api(f"/containers/create?name={quote(name, safe='')}", data=config)
    if not created or not created.get("Id"):
        return None
    container_id = created["Id"]
    if _docker_api(f"/containers/{container_id}/start", method="post") is None:
        _docker_api(f"/containers/{container_id}?force=true", method="delete")
        return None
    inspected = _docker_api(f"/containers/{container_id}/json", method="get") or {}
    ip = inspected.get("NetworkSettings", {}).get("Networks", {}).get(network, {}).get("IPAddress", "")
    return container_id, ip


def _remove_container(container_id):
    if container_id:
        _docker_api(f"/containers/{container_id}/stop?t=5", method="post")
        _docker_api(f"/containers/{container_id}?force=true", method="delete")


def _fail(session, container_ids, network):
    for container_id in container_ids:
        _remove_container(container_id)
    _remove_network(network)
    _release_ports(session)
    session.status = SandboxSession.ERROR
    session.save(update_fields=["status"])
    return None


def deploy_sandbox(session):
    """Pull and run the images selected on the lab in an isolated Docker network."""
    lab = session.lab
    profile = lab.resource_profile
    terminal = lab.terminal_container
    services = list(lab.service_containers.all())
    if terminal is None:
        logger.error("Lab %s has no ttyd terminal container selected", lab.id)
        return _fail(session, [], None)

    selected = [terminal, *services]
    if not all(_ensure_image(container.image) for container in selected):
        return _fail(session, [], None)

    ports = _reserve_ports(session, len(selected))
    if len(ports) != len(selected):
        logger.error("Port range %s-%s is exhausted", settings.DOCKER_PORT_START, settings.DOCKER_PORT_END)
        return _fail(session, [], None)

    network = _create_network()
    if not network:
        return _fail(session, [], None)

    created_ids = []
    endpoints = []
    # Start target services first so their private IPs are available in the terminal.
    for index, service in enumerate(services, start=1):
        result = _create_container(
            service.image, f"somacloud-s{session.id}-{index}", network, profile,
            ports[index], service.container_port, command=service.command,
        )
        if not result:
            return _fail(session, created_ids, network)
        container_id, ip = result
        created_ids.append(container_id)
        endpoints.append({
            "name": service.name, "image": service.image, "ip": ip,
            "container_port": service.container_port, "host_port": ports[index],
            "container_id": container_id,
        })

    first_ip = endpoints[0]["ip"] if endpoints else ""
    terminal_result = _create_container(
        terminal.image, f"somacloud-t{session.id}", network, profile, ports[0], terminal.container_port,
        env={"LAB_TITLE": lab.title, "SERVICE_IP": first_ip, "SERVICE_ENDPOINTS": ",".join(e["ip"] for e in endpoints)},
        command=terminal.command,
    )
    if not terminal_result:
        return _fail(session, created_ids, network)
    terminal_id, _ = terminal_result

    session.container_id = terminal_id
    session.service_container_id = created_ids[0] if created_ids else ""
    session.service_container_ids = created_ids
    session.service_ip = first_ip
    session.service_port = endpoints[0]["host_port"] if endpoints else None
    session.service_endpoints = endpoints
    session.terminal_port = ports[0]
    session.network_name = network
    session.server_url = f"{settings.DOCKER_PUBLIC_SCHEME}://{settings.DOCKER_SERVER_PUBLIC_IP}"
    session.terminal_url = f"{session.server_url}:{session.terminal_port}/"
    session.status = SandboxSession.RUNNING
    session.expires_at = timezone.now() + timedelta(minutes=profile.time_limit_minutes)
    session.save()
    return session


def stop_sandbox(session, status=SandboxSession.STOPPED):
    container_ids = [session.container_id, *session.service_container_ids]
    # Older sessions created by the legacy provisioner only have service_container_id.
    if session.service_container_id and session.service_container_id not in container_ids:
        container_ids.append(session.service_container_id)
    for container_id in filter(None, container_ids):
        _remove_container(container_id)
    _remove_network(session.network_name)
    _release_ports(session)
    session.status = status
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])


def get_sandbox_status(session):
    if session.status != SandboxSession.RUNNING:
        return session.status
    inspected = _docker_api(f"/containers/{session.container_id}/json", method="get")
    if inspected and inspected.get("State", {}).get("Running"):
        return SandboxSession.RUNNING
    session.status = SandboxSession.STOPPED
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])
    _release_ports(session)
    return SandboxSession.STOPPED


def expire_stale_sessions():
    expired = SandboxSession.objects.filter(status=SandboxSession.RUNNING, expires_at__lte=timezone.now())
    count = expired.count()
    for session in expired:
        stop_sandbox(session, status=SandboxSession.EXPIRED)
    return count
