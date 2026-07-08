from core.orchestrator import build_service_image, _docker_api


DEFAULT_DOCKERFILE = """FROM php:8.1-apache
RUN docker-php-ext-install pdo pdo_sqlite
RUN a2enmod rewrite
"""


def deploy_default(network, host_port, flag, dockerfile=None, files=None, image_tag=None, internal_port=80, env=None):
    image_tag = image_tag or f"somacloud-service-{flag.lower().replace('{','').replace('}','').replace('_','-')}:latest"
    build_service_image(image_tag, dockerfile or DEFAULT_DOCKERFILE, files)

    env = env or {}
    env.setdefault("FLAG", flag)

    env_list = [f"{k}={v}" for k, v in env.items()]
    config = {
        "Image": image_tag,
        "HostConfig": {
            "PortBindings": {f"{internal_port}/tcp": [{"HostPort": str(host_port)}]}
        },
        "Env": env_list,
        "ExposedPorts": {f"{internal_port}/tcp": {}},
    }

    result = _docker_api("/containers/create", data=config)
    if not result or "Id" not in result:
        return None, "", ""

    cid = result["Id"]
    _docker_api(f"/networks/{network}/connect", data={"Container": cid})
    _docker_api(f"/containers/{cid}/start", method="post")

    inspect = _docker_api(f"/containers/{cid}/json", method="get")
    ip = ""
    if inspect:
        nets = inspect.get("NetworkSettings", {}).get("Networks", {})
        ip = nets.get(network, {}).get("IPAddress", "")
    return cid, ip, flag
