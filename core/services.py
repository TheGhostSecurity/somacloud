from django.db.models import Count, Q

from .models import Activity, Enrollment, Lab, LabEnrollment, LabProgress, Progress


def enrolled_learning_paths_for(user):
    return (
        Enrollment.objects.filter(user=user, is_active=True)
        .select_related("learning_path")
        .prefetch_related("learning_path__modules__activities__stages")
    )


def activity_completion(user, activity):
    stage_count = activity.stages.count()
    if not stage_count:
        return {"completed": 0, "total": 0, "percent": 0, "is_complete": False}

    completed = Progress.objects.filter(
        user=user,
        activity_stage__activity=activity,
        completed_at__isnull=False,
    ).count()
    percent = round((completed / stage_count) * 100)
    return {
        "completed": completed,
        "total": stage_count,
        "percent": percent,
        "is_complete": completed == stage_count,
    }


def dashboard_summary_for(user):
    enrolled_paths = enrolled_learning_paths_for(user)
    path_ids = [enrollment.learning_path_id for enrollment in enrolled_paths]
    activities = Activity.objects.filter(module__learning_path_id__in=path_ids, is_published=True)
    stage_total = activities.aggregate(total=Count("stages"))["total"] or 0
    completed_stages = Progress.objects.filter(
        user=user,
        activity_stage__activity__in=activities,
        completed_at__isnull=False,
    ).count()
    completed_activities = 0

    for activity in activities.prefetch_related("stages"):
        completion = activity_completion(user, activity)
        if completion["is_complete"]:
            completed_activities += 1

    return {
        "enrolled_paths": len(path_ids),
        "total_activities": activities.count(),
        "completed_activities": completed_activities,
        "completed_stages": completed_stages,
        "total_stages": stage_total,
        "percent": round((completed_stages / stage_total) * 100) if stage_total else 0,
    }


def next_activity_for(user):
    enrollments = enrolled_learning_paths_for(user)
    for enrollment in enrollments:
        modules = enrollment.learning_path.modules.filter(is_published=True).prefetch_related("activities__stages")
        for module in modules:
            activities = module.activities.filter(is_published=True)
            for activity in activities:
                if not activity_completion(user, activity)["is_complete"]:
                    return activity
    return None


def mark_stage_complete(user, activity_stage):
    progress, _ = Progress.objects.get_or_create(user=user, activity_stage=activity_stage)
    progress.mark_complete()
    activity = activity_stage.activity
    return activity_completion(user, activity)


def learning_path_cards_for(user):
    cards = []
    for enrollment in enrolled_learning_paths_for(user):
        path = enrollment.learning_path
        activities = Activity.objects.filter(module__learning_path=path, is_published=True).annotate(
            stage_count=Count("stages"),
            completed_count=Count(
                "stages__progress_entries",
                filter=Q(stages__progress_entries__user=user, stages__progress_entries__completed_at__isnull=False),
            ),
        )
        total_stages = sum(activity.stage_count for activity in activities)
        completed_stages = sum(activity.completed_count for activity in activities)
        cards.append(
            {
                "path": path,
                "activity_count": activities.count(),
                "percent": round((completed_stages / total_stages) * 100) if total_stages else 0,
            }
        )
    return cards


def lab_progress_for(user, lab):
    stages = [s[0] for s in LabProgress.STAGE_CHOICES]
    completed = {}
    for entry in LabProgress.objects.filter(user=user, lab=lab, completed_at__isnull=False):
        completed[entry.stage] = True
    results = []
    for stage in stages:
        results.append({"stage": stage, "completed": stage in completed})
    total = len(stages)
    done = len(completed)
    return {
        "stages": results,
        "completed": done,
        "total": total,
        "percent": round((done / total) * 100) if total else 0,
        "is_complete": done == total,
    }


def mark_lab_stage_complete(user, lab, stage):
    progress, _ = LabProgress.objects.get_or_create(user=user, lab=lab, stage=stage)
    progress.mark_complete()
    return lab_progress_for(user, lab)


def enrolled_labs_for(user):
    return LabEnrollment.objects.filter(user=user, is_active=True).select_related("lab__hack_phase", "lab__resource_profile")


def next_lab_for(user):
    enrollments = enrolled_labs_for(user)
    for enrollment in enrollments:
        progress = lab_progress_for(user, enrollment.lab)
        if not progress["is_complete"]:
            return enrollment.lab
    return None
