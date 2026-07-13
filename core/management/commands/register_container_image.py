from django.core.management.base import BaseCommand, CommandError

from core.models import ContainerImage


class Command(BaseCommand):
    help = "Register or update a Docker Hub image that instructors can select for labs."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--image", required=True)
        parser.add_argument("--kind", required=True, choices=[ContainerImage.TERMINAL, ContainerImage.SERVICE])
        parser.add_argument("--port", required=True, type=int, dest="container_port")
        parser.add_argument("--description", default="")
        parser.add_argument("--command", default="")

    def handle(self, *args, **options):
        if options["container_port"] < 1 or options["container_port"] > 65535:
            raise CommandError("--port must be between 1 and 65535.")
        image, created = ContainerImage.objects.update_or_create(
            image=options["image"],
            defaults={
                "name": options["name"], "kind": options["kind"],
                "container_port": options["container_port"],
                "description": options["description"], "command": options["command"],
            },
        )
        state = "Registered" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{state} {image.kind} image: {image.image}"))
