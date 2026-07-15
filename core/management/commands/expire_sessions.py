from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import SandboxSession
from core.orchestrator import expire_stale_sessions


class Command(BaseCommand):
    help = "Expire stale sandbox sessions past their expires_at and clean up Docker resources"

    def handle(self, *args, **options):
        count = expire_stale_sessions()
        if count:
            self.stdout.write(f"Expired {count} stale session(s)")
        else:
            self.stdout.write("No stale sessions found")
