import logging
import os
import uuid
from urllib.parse import quote

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DockerNode, PortReservation, SandboxSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node selection
# ---------------------------------------------------------------------------

def select_node():
    """Pick the least-loaded active node. Falls back to local Docker if none registered."""
    nodes = DockerNode.objects.filter(status=DockerNode.ACTIVE).order_by("current_sessions", "name")
    if nodes.exists():
        return nodes.first()
    return None


def get_node_docker_host(node=None):
    """Return the Docker API base URL for a node, or the manager fallback."""
    if node and node.docker_host:
        return node.docker_host
    return settings.DOCKER_HOST


# ---------------------------------------------------------------------------
# Docker API transport
# ---------------------------------------------------------------------------

def _tls_kwargs(node=None):
    """Build the TLS verify/cert kwargs for requests."""
    if node:
        cert_dir = os.path.join(settings.DOCKER_TLS_CERT_DIR, node.name)
    else:
        cert_dir = settings.DOCKER_TLS_CERT_DIR
    kwargs = {}
    if settings.DOCKER_TLS_VERIFY:
        kwargs["verify"] = os.path.join(cert_dir, settings.DOCKER_TLS_CA_FILE)
        kwargs["cert"] = (
            os.path.join(cert_dir, settings.DOCKER_TLS_CERT_FILE),
            os.path.join(cert_dir, settings.DOCKER_TLS_KEY_FILE),
        )
    return kwargs


def _docker_api(path, method="post", data=None, timeout=None, node=None):
    """Make an authenticated call to Docker's Remote API.

    If *node* is provided the request is routed to that worker node's Docker
    daemon; otherwise it hits the manager (local) daemon.
    """
    base_url = get_node_docker_host(node)
    kwargs = {
        "headers": {"Content-Type": "application/json"},
        "timeout": timeout or settings.DOCKER_API_TIMEOUT,
    }
    kwargs.update(_tls_kwargs(node))
    if data is not None:
        kwargs["json"] = data
    try:
        response = requests.request(method, f"{base_url}{path}", **kwargs)
        response.raise_for_status()
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}
    except (requests.RequestException, OSError) as exc:
        label = node.name if node else "manager"
        logger.error("Docker API %s %s on %s failed: %s", method.upper(), path, label, exc)
        return None


# ---------------------------------------------------------------------------
# Image management
# ---------------------------------------------------------------------------

def _ensure_image(image, node=None):
    encoded = quote(image, safe="")
    if _docker_api(f"/images/{encoded}/json", method="get", node=node) is not None:
        return True
    logger.info("Pulling Docker image %s on %s", image, node.name if node else "manager")
    if _docker_api(f"/images/create?fromImage={encoded}", method="post", timeout=300, node=node) is None:
        return False
    return _docker_api(f"/images/{encoded}/json", method="get", node=node) is not None


# ---------------------------------------------------------------------------
# Network management (per-node bridge)
# ---------------------------------------------------------------------------

def _create_network(node=None):
    name = f"somacloud-{uuid.uuid4().hex[:12]}"
    result = _docker_api(
        "/networks/create",
        data={"Name": name, "Driver": "bridge", "Labels": {"somacloud.managed": "true"}},
        node=node,
    )
    return name if result and result.get("Id") else None


def _remove_network(name, node=None):
    if name:
        _docker_api(f"/networks/{quote(name, safe='')}", method="delete", node=node)


# ---------------------------------------------------------------------------
# Port reservation (per-node ranges)
# ---------------------------------------------------------------------------

def _docker_used_ports(node=None):
    containers = _docker_api("/containers/json?all=1", method="get", node=node) or []
    return {
        port.get("PublicPort")
        for container in containers
        for port in container.get("Ports", [])
        if port.get("PublicPort")
    }


def _reserve_ports(session, count, node=None):
    """Atomically reserve ports in the node's configured range for one sandbox."""
    port_start = node.port_start if node else settings.DOCKER_PORT_START
    port_end = node.port_end if node else settings.DOCKER_PORT_END
    unavailable = _docker_used_ports(node)
    reserved = []
    for port in range(port_start, port_end + 1):
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


# ---------------------------------------------------------------------------
# Container lifecycle
# ---------------------------------------------------------------------------

def _resources(profile, network, port, container_port):
    port_key = f"{container_port}/tcp"
    return {
        "NetworkMode": network,
        "Memory": int(profile.memory_mb * 1024 * 1024),
        "MemorySwap": int(profile.memory_mb * 1024 * 1024),
        "NanoCpus": int(profile.cpu_count * 1_000_000_000),
        "PortBindings": {port_key: [{"HostPort": str(port)}]},
    }


def _create_container(image, name, network, profile, host_port, container_port, env=None, command="", node=None):
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
    created = _docker_api(f"/containers/create?name={quote(name, safe='')}", data=config, node=node)
    if not created or not created.get("Id"):
        return None
    container_id = created["Id"]
    if _docker_api(f"/containers/{container_id}/start", method="post", node=node) is None:
        _docker_api(f"/containers/{container_id}?force=true", method="delete", node=node)
        return None
    inspected = _docker_api(f"/containers/{container_id}/json", method="get", node=node) or {}
    ip = inspected.get("NetworkSettings", {}).get("Networks", {}).get(network, {}).get("IPAddress", "")
    return container_id, ip


def _remove_container(container_id, node=None):
    if container_id:
        _docker_api(f"/containers/{container_id}/stop?t=5", method="post", node=node)
        _docker_api(f"/containers/{container_id}?force=true", method="delete", node=node)


# ---------------------------------------------------------------------------
# Failure cleanup
# ---------------------------------------------------------------------------

def _fail(session, container_ids, network, node=None):
    for container_id in container_ids:
        _remove_container(container_id, node=node)
    _remove_network(network, node=node)
    _release_ports(session)
    session.status = SandboxSession.ERROR
    session.save(update_fields=["status"])
    if node:
        DockerNode.objects.filter(pk=node.pk).update(
            current_sessions=models.F("current_sessions") - 1
        )
    return None


# ---------------------------------------------------------------------------
# Deploy / Stop / Status
# ---------------------------------------------------------------------------

def deploy_sandbox(session):
    """Pick a node, pull images, and run the sandbox containers on it."""
    from django.db import models as db_models

    lab = session.lab
    profile = lab.resource_profile
    terminal = lab.terminal_container
    services = list(lab.service_containers.all())
    if terminal is None:
        logger.error("Lab %s has no ttyd terminal container selected", lab.id)
        return _fail(session, [], None)

    node = select_node()
    if node is None:
        logger.error("No active Docker nodes available")
        session.status = SandboxSession.ERROR
        session.save(update_fields=["status"])
        return None

    # Pull images on the target node
    selected = [terminal, *services]
    if not all(_ensure_image(container.image, node=node) for container in selected):
        return _fail(session, [], None, node=node)

    # Reserve ports on the target node
    ports = _reserve_ports(session, len(selected), node=node)
    if len(ports) != len(selected):
        logger.error("Port range %s-%s exhausted on node %s", node.port_start, node.port_end, node.name)
        return _fail(session, [], None, node=node)

    # Create isolated network on the target node
    network = _create_network(node=node)
    if not network:
        return _fail(session, [], None, node=node)

    # Bump session count before starting containers
    DockerNode.objects.filter(pk=node.pk).update(current_sessions=db_models.F("current_sessions") + 1)
    session.node = node

    created_ids = []
    endpoints = []
    # Start target services first so their private IPs are available in the terminal.
    for index, service in enumerate(services, start=1):
        result = _create_container(
            service.image, f"somacloud-s{session.id}-{index}", network, profile,
            ports[index], service.container_port, command=service.command, node=node,
        )
        if not result:
            return _fail(session, created_ids, network, node=node)
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
        command=terminal.command, node=node,
    )
    if not terminal_result:
        return _fail(session, created_ids, network, node=node)
    terminal_id, _ = terminal_result

    session.container_id = terminal_id
    session.service_container_id = created_ids[0] if created_ids else ""
    session.service_container_ids = created_ids
    session.service_ip = first_ip
    session.service_port = endpoints[0]["host_port"] if endpoints else None
    session.service_endpoints = endpoints
    session.terminal_port = ports[0]
    session.network_name = network
    session.server_url = f"{settings.DOCKER_PUBLIC_SCHEME}://{node.public_ip}"
    session.terminal_url = f"{session.server_url}:{session.terminal_port}/"
    session.status = SandboxSession.RUNNING
    session.save()
    return session


def stop_sandbox(session, status=SandboxSession.STOPPED):
    from django.db import models as db_models

    node = session.node
    container_ids = [session.container_id, *session.service_container_ids]
    if session.service_container_id and session.service_container_id not in container_ids:
        container_ids.append(session.service_container_id)
    for container_id in filter(None, container_ids):
        _remove_container(container_id, node=node)
    _remove_network(session.network_name, node=node)
    _release_ports(session)
    session.status = status
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])
    # Decrement node session count
    if node:
        DockerNode.objects.filter(pk=node.pk).update(current_sessions=db_models.F("current_sessions") - 1)


def get_sandbox_status(session):
    if session.status != SandboxSession.RUNNING:
        return session.status
    inspected = _docker_api(f"/containers/{session.container_id}/json", method="get", node=session.node)
    if inspected and inspected.get("State", {}).get("Running"):
        return SandboxSession.RUNNING
    session.status = SandboxSession.STOPPED
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])
    _release_ports(session)
    if session.node:
        from django.db import models as db_models
        DockerNode.objects.filter(pk=session.node.pk).update(
            current_sessions=db_models.F("current_sessions") - 1
        )
    return SandboxSession.STOPPED


def expire_stale_sessions():
    expired = SandboxSession.objects.filter(status=SandboxSession.RUNNING, expires_at__lte=timezone.now())
    count = expired.count()
    for session in expired:
        stop_sandbox(session, status=SandboxSession.EXPIRED)
    return count
