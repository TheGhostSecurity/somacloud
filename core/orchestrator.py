import io
import json
import logging
import tarfile
import uuid
from datetime import timedelta
from urllib.parse import quote

import requests
from django.conf import settings
from django.utils import timezone

from .models import Lab, SandboxSession

logger = logging.getLogger(__name__)


def _docker_api(path, method="post", data=None, headers=None, stream=False, timeout=None):
    url = f"{settings.DOCKER_HOST}{path}"
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    try:
        kwargs = {"headers": hdrs, "timeout": timeout or 10, "stream": stream}
        if isinstance(data, dict):
            kwargs["json"] = data
        else:
            kwargs["data"] = data
        if method == "post":
            resp = requests.post(url, **kwargs)
        elif method == "get":
            resp = requests.get(url, **kwargs)
        elif method == "delete":
            resp = requests.delete(url, **kwargs)
        else:
            return None
        resp.raise_for_status()
        if stream:
            return resp
        return resp.json() if resp.content else {}
    except requests.RequestException as e:
        logger.error("Docker API error on %s: %s", path, e)
        return None


def _create_network():
    name = f"sandbox-{uuid.uuid4().hex[:12]}"
    result = _docker_api("/networks/create", data={"Name": name, "Driver": "bridge"})
    if result and "Id" in result:
        return name, result
    return name, None


def _remove_network(name):
    _docker_api(f"/networks/{name}", method="delete")


def _allocate_port():
    start = settings.DOCKER_SERVICE_PORT_START
    end = settings.DOCKER_SERVICE_PORT_END
    used = set(
        SandboxSession.objects.filter(
            status__in=[SandboxSession.RUNNING, SandboxSession.PENDING]
        ).exclude(service_port=None).values_list("service_port", flat=True)
    )
    for port in range(start, end + 1):
        if port not in used:
            return port
    logger.error("No available ports in range %s-%s", start, end)
    return None


def _release_port(session):
    session.service_port = None
    session.save(update_fields=["service_port"])


def _check_image_exists(tag):
    encoded = quote(tag, safe='')
    result = _docker_api(f"/images/{encoded}/json", method="get")
    return result is not None


def _ensure_image(tag):
    if _check_image_exists(tag):
        return True
    logger.info("Pulling image %s ...", tag)
    encoded = quote(tag, safe='')
    resp = _docker_api(f"/images/create?fromImage={encoded}", method="post", timeout=300)
    if resp is None:
        logger.error("Failed to pull image %s", tag)
        return False
    return _check_image_exists(tag)


def _build_image_from_files(tag, dockerfile_content, files=None):
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        df_bytes = dockerfile_content.encode("utf-8")
        info = tarfile.TarInfo(name="Dockerfile")
        info.size = len(df_bytes)
        info.mtime = int(timezone.now().timestamp())
        tar.addfile(info, io.BytesIO(df_bytes))

        for fname, fcontent in (files or {}).items():
            f_bytes = fcontent.encode("utf-8") if isinstance(fcontent, str) else fcontent
            info = tarfile.TarInfo(name=fname)
            info.size = len(f_bytes)
            info.mtime = int(timezone.now().timestamp())
            tar.addfile(info, io.BytesIO(f_bytes))

    tar_stream.seek(0)

    resp = _docker_api(
        f"/build?t={tag}&dockerfile=Dockerfile&rm=true",
        method="post",
        data=tar_stream,
        headers={"Content-Type": "application/x-tar"},
        stream=True,
        timeout=120,
    )
    if resp is None:
        return False
    for line in resp.iter_lines(decode_unicode=True):
        if line:
            try:
                msg = json.loads(line)
                if "error" in msg:
                    logger.error("Docker build error: %s", msg["error"])
                    return False
            except json.JSONDecodeError:
                pass
    return _check_image_exists(tag)


def _create_container(image, network, host_config=None, env=None, command=None):
    env_list = [f"{k}={v}" for k, v in (env or {}).items()]
    config = {
        "Image": image,
        "HostConfig": host_config or {},
        "AttachStdin": True,
        "AttachStdout": True,
        "OpenStdin": True,
        "Tty": True,
    }
    if env_list:
        config["Env"] = env_list
    if command:
        config["Cmd"] = command if isinstance(command, list) else command.split()

    result = _docker_api("/containers/create", data=config)
    if not result or "Id" not in result:
        return None

    cid = result["Id"]
    _docker_api(f"/networks/{network}/connect", data={"Container": cid})
    _docker_api(f"/containers/{cid}/start", method="post")

    inspect = _docker_api(f"/containers/{cid}/json", method="get")
    ip = ""
    if inspect:
        nets = inspect.get("NetworkSettings", {}).get("Networks", {})
        ip = nets.get(network, {}).get("IPAddress", "")
    return cid, ip


def deploy_sandbox(session):
    lab = session.lab
    profile = lab.resource_profile
    expiry = timezone.now() + timedelta(minutes=profile.time_limit_minutes)

    kali_image = lab.sandbox_image or settings.DOCKER_DEFAULT_IMAGE
    network_name, _ = _create_network()
    if not network_name:
        session.status = SandboxSession.ERROR
        session.save(update_fields=["status"])
        return None

    service_cid = None
    service_ip = ""
    service_flag = ""
    service_port = None

    if lab.scenario_service:
        try:
            import importlib
            mod = importlib.import_module(lab.scenario_service.script_module)
            external_port = _allocate_port()
            if external_port is None:
                logger.error("Port allocation failed for sandbox session %s", session.id)
            else:
                result = mod.deploy(network=network_name, host_port=external_port)
                if result:
                    service_cid, service_ip, service_flag = result
                    service_port = external_port
        except Exception as e:
            logger.error("Scenario service deployment failed: %s", e)

    host_config = {
        "Memory": profile.memory_mb * 1024 * 1024,
        "NanoCpus": profile.cpu_count * 1_000_000_000,
        "MemorySwap": profile.memory_mb * 1024 * 1024,
    }

    if not _ensure_image(kali_image):
        logger.error("Kali image %s not available", kali_image)
        _remove_network(network_name)
        session.status = SandboxSession.ERROR
        session.save(update_fields=["status"])
        return None

    kali_result = _create_container(
        image=kali_image,
        network=network_name,
        host_config=host_config,
        env={"LAB_TITLE": lab.title, "SERVICE_IP": service_ip, "FLAG": service_flag},
    )

    if not kali_result:
        _remove_network(network_name)
        session.status = SandboxSession.ERROR
        session.save(update_fields=["status"])
        return None

    kali_cid, _ = kali_result

    server_ip = settings.DOCKER_SERVER_PUBLIC_IP
    ttyd_port = settings.DOCKER_TERMINAL_PORT

    session.container_id = kali_cid
    session.service_container_id = service_cid or ""
    session.service_ip = service_ip
    session.service_port = service_port
    session.server_url = f"http://{server_ip}"
    session.terminal_url = f"http://{server_ip}:{ttyd_port}/"
    session.status = SandboxSession.RUNNING
    session.expires_at = expiry
    session.save(
        update_fields=[
            "container_id", "service_container_id", "service_ip", "service_port",
            "server_url", "terminal_url", "status", "expires_at",
        ]
    )

    return session


def stop_sandbox(session):
    if session.container_id:
        _docker_api(f"/containers/{session.container_id}/stop", method="post")
        _docker_api(f"/containers/{session.container_id}", method="delete")
    if session.service_container_id:
        _docker_api(f"/containers/{session.service_container_id}/stop", method="post")
        _docker_api(f"/containers/{session.service_container_id}", method="delete")
    session.status = SandboxSession.STOPPED
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])
    _release_port(session)


def get_sandbox_status(session):
    if session.status != SandboxSession.RUNNING:
        return session.status
    inspect = _docker_api(f"/containers/{session.container_id}/json", method="get")
    if inspect and inspect.get("State", {}).get("Running"):
        return SandboxSession.RUNNING
    session.status = SandboxSession.STOPPED
    session.stopped_at = timezone.now()
    session.save(update_fields=["status", "stopped_at"])
    _release_port(session)
    return SandboxSession.STOPPED


def expire_stale_sessions():
    expired = SandboxSession.objects.filter(
        status=SandboxSession.RUNNING, expires_at__lte=timezone.now()
    )
    for session in expired:
        stop_sandbox(session)
        session.status = SandboxSession.EXPIRED
        session.save(update_fields=["status"])


def build_service_image(tag, dockerfile_content, files=None):
    if _check_image_exists(tag):
        return True
    return _build_image_from_files(tag, dockerfile_content, files)
