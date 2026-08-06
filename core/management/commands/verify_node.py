from django.core.management.base import BaseCommand, CommandError

from core.models import DockerNode
from core.orchestrator import verify_node


class Command(BaseCommand):
    help = "Run a full smoke test on a Docker worker node."

    def add_arguments(self, parser):
        parser.add_argument("--name", help="Node name (e.g. worker-1)")
        parser.add_argument("--id", type=int, dest="node_id", help="Node database ID")

    def handle(self, *args, **options):
        name = options.get("name")
        node_id = options.get("node_id")
        if name:
            node = DockerNode.objects.filter(name=name).first()
        elif node_id:
            node = DockerNode.objects.filter(pk=node_id).first()
        else:
            raise CommandError("Specify --name or --id")
        if not node:
            raise CommandError(f"Node not found")
        results, passed = verify_node(node)
        for r in results:
            icon = "✓" if r["status"] == "pass" else "✗" if r["status"] == "fail" else "?"
            self.stdout.write(f"  {icon} {r['step']}: {r['detail']}")
        if passed:
            self.stdout.write(self.style.SUCCESS(f"Verify passed for {node.name}"))
        else:
            self.stdout.write(self.style.ERROR(f"Verify FAILED for {node.name}"))
