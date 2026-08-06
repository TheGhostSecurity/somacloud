from django.core.management.base import BaseCommand

from core.models import DockerNode
from core.orchestrator import verify_node


class Command(BaseCommand):
    help = "Register a Docker worker node."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Node name (e.g. worker-1)")
        parser.add_argument("--docker-node-id", default="", help="Swarm node ID")
        parser.add_argument("--public-ip", required=True, help="Public IP address")
        parser.add_argument("--docker-host", required=True, help="Docker API URL (e.g. https://16.192.120.188:2376)")
        parser.add_argument("--port-start", type=int, default=9000, help="Start of port range")
        parser.add_argument("--port-end", type=int, default=9100, help="End of port range")
        parser.add_argument("--total-cpu", type=float, default=2.0, help="Total CPU cores")
        parser.add_argument("--total-memory", type=int, default=3500, help="Total memory in MB")
        parser.add_argument("--verify", action="store_true", help="Run smoke test after registration")

    def handle(self, *args, **options):
        name = options["name"]
        if DockerNode.objects.filter(name=name).exists():
            self.stdout.write(self.style.ERROR(f"Node '{name}' already exists."))
            return

        node = DockerNode.objects.create(
            name=name,
            docker_node_id=options["docker_node_id"],
            public_ip=options["public_ip"],
            docker_host=options["docker_host"],
            port_start=options["port_start"],
            port_end=options["port_end"],
            total_cpu=options["total_cpu"],
            total_memory_mb=options["total_memory"],
        )
        self.stdout.write(self.style.SUCCESS(f"Registered node '{name}' (ID: {node.id})"))

        if options["verify"]:
            self.stdout.write("Running verification…")
            results, passed = verify_node(node)
            for r in results:
                icon = "✓" if r["status"] == "pass" else "✗" if r["status"] == "fail" else "?"
                self.stdout.write(f"  {icon} {r['step']}: {r['detail']}")
            if passed:
                self.stdout.write(self.style.SUCCESS(f"Verify passed for {node.name}"))
            else:
                self.stdout.write(self.style.ERROR(f"Verify FAILED for {node.name}"))
