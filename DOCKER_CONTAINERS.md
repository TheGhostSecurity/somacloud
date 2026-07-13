# Docker image based labs

SomaCloud no longer builds or imports scenario-service Python modules. Register each vetted Docker Hub image once, then instructors select a ttyd image and any number of vulnerable services when creating a lab.

```sh
python manage.py migrate
python manage.py register_container_image \
  --name "Kali ttyd" --kind terminal \
  --image "<your-docker-hub-namespace>/kali-ttyd:latest" --port 7681

python manage.py register_container_image \
  --name "SQL injection target" --kind service \
  --image "<your-docker-hub-namespace>/sqli-lab:latest" --port 80
```

Use the port exposed *inside* each container. When a student launches a sandbox, SomaCloud pulls missing selected images through Docker's TLS API at `https://16.16.138.119:2376`, creates a private bridge network, and runs the selected target containers and ttyd terminal inside it. Every container receives the lab resource profile and a unique published host port from `9000` through `9100`.

The terminal is available at `http://16.16.138.119:<allocated-port>/`. Targets can be reached from the terminal using their private IP and container port. Notes may use `{{SERVICE_IP}}` for the first target or `{{SERVICE_ENDPOINTS}}` for all targets.

Set `DOCKER_HOST`, `DOCKER_TLS_CERT_PATH`, `DOCKER_SERVER_PUBLIC_IP`, `DOCKER_PORT_START`, and `DOCKER_PORT_END` as environment variables to override the defaults. The defaults match this host's `ca.pem`, `client-cert.pem`, and `client-key.pem`; use `DOCKER_TLS_CA_FILE`, `DOCKER_TLS_CERT_FILE`, and `DOCKER_TLS_KEY_FILE` if yours differ.
