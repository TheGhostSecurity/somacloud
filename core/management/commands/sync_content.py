import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.content_loader import CONTENT_ROOT, load_simple_yaml, relative_content_path
from core.models import Activity, ActivityStage, Assessment, LearningPath, Module, ResourceProfile


STAGE_FILES = (
    (ActivityStage.THEORY, "Theory", "theory.md", None),
    (ActivityStage.GUIDED_PRACTICE, "Guided Practice", "practice.md", None),
    (ActivityStage.SANDBOX, "Sandbox", None, "sandbox.yaml"),
    (ActivityStage.CHALLENGE, "Challenge", "challenge.md", None),
    (ActivityStage.REFLECTION, "Reflection", "reflection.md", None),
    (ActivityStage.ASSESSMENT, "Assessment", "assessment.json", None),
)


class Command(BaseCommand):
    help = "Sync learning paths, modules, activities, and stage file references from content/."

    def add_arguments(self, parser):
        parser.add_argument("--content-root", default=str(CONTENT_ROOT), help="Path to the content directory.")

    def handle(self, *args, **options):
        root = Path(options["content_root"])
        if not root.exists():
            raise CommandError(f"Content root does not exist: {root}")

        path_count = module_count = activity_count = stage_count = 0

        for path_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            path_meta = load_simple_yaml(path_dir / "path.yaml")
            learning_path, _ = LearningPath.objects.update_or_create(
                slug=path_dir.name,
                defaults={
                    "title": path_meta.get("title", path_dir.name.replace("-", " ").title()),
                    "description": path_meta.get("description", ""),
                    "order": path_meta.get("order", 0),
                    "is_published": path_meta.get("is_published", True),
                },
            )
            path_count += 1

            for module_dir in sorted(path for path in path_dir.iterdir() if path.is_dir()):
                module_meta = load_simple_yaml(module_dir / "module.yaml")
                module, _ = Module.objects.update_or_create(
                    learning_path=learning_path,
                    slug=module_dir.name,
                    defaults={
                        "title": module_meta.get("title", module_dir.name.replace("-", " ").title()),
                        "description": module_meta.get("description", ""),
                        "order": module_meta.get("order", 0),
                        "is_published": module_meta.get("is_published", True),
                    },
                )
                module_count += 1

                for activity_dir in sorted(path for path in module_dir.iterdir() if path.is_dir()):
                    activity_meta = load_simple_yaml(activity_dir / "activity.yaml")
                    resource = self._resource_profile(activity_meta)
                    activity, _ = Activity.objects.update_or_create(
                        module=module,
                        slug=activity_dir.name,
                        defaults={
                            "resource_profile": resource,
                            "title": activity_meta.get("title", activity_dir.name.replace("-", " ").title()),
                            "summary": activity_meta.get("summary", ""),
                            "order": activity_meta.get("order", 0),
                            "is_published": activity_meta.get("is_published", True),
                        },
                    )
                    activity_count += 1
                    stage_count += self._sync_stages(activity, activity_dir)
                    self._sync_assessment(activity, activity_dir / "assessment.json")

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {path_count} paths, {module_count} modules, {activity_count} activities, {stage_count} stages."
            )
        )

    def _resource_profile(self, metadata):
        name = metadata.get("resource_profile", "Light")
        resource, _ = ResourceProfile.objects.update_or_create(
            name=name,
            defaults={
                "cpu_count": metadata.get("resource_cpu", 1),
                "memory_mb": metadata.get("resource_memory_mb", 256),
                "time_limit_minutes": metadata.get("resource_time_limit_minutes", 5),
            },
        )
        return resource

    def _sync_stages(self, activity, activity_dir):
        synced_stage_types = []
        count = 0

        for stage_type, title, content_filename, config_filename in STAGE_FILES:
            content_path = activity_dir / content_filename if content_filename else None
            config_path = activity_dir / config_filename if config_filename else None

            if content_path and not content_path.exists():
                continue
            if config_path and not config_path.exists():
                continue

            defaults = {
                "title": title,
                "content": "",
                "content_file": relative_content_path(content_path) if content_path else "",
                "config_file": relative_content_path(config_path) if config_path else "",
                "order": ActivityStage.DEFAULT_STAGE_ORDER[stage_type],
            }
            ActivityStage.objects.update_or_create(activity=activity, stage_type=stage_type, defaults=defaults)
            synced_stage_types.append(stage_type)
            count += 1

        ActivityStage.objects.filter(activity=activity).exclude(stage_type__in=synced_stage_types).delete()
        return count

    def _sync_assessment(self, activity, assessment_path):
        if not assessment_path.exists():
            return
        with assessment_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        Assessment.objects.update_or_create(
            activity=activity,
            defaults={
                "instructions": data.get("instructions", ""),
                "passing_score": data.get("passing_score", 70),
            },
        )
