import io
import json
import logging
import uuid
from datetime import timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .content_loader import render_markdown
from . import ca
from .forms import (
    DockerNodeForm,
    LabForm,
    ResourceProfileForm,
    SignUpForm,
    SSHKeyUploadForm,
    StudentProfileImageForm,
    UserManagementForm,
    UserProfileForm,
    assign_role,
    get_role_label,
)
from .models import (
    Activity,
    ContainerImage,
    DockerNode,
    FlagSubmission,
    HackPhase,
    Lab,
    LabEnrollment,
    LabProgress,
    LearningPath,
    Module,
    ResourceProfile,
    SandboxSession,
    SSHKey,
    StudentProfile,
    Tool,
)
from .orchestrator import _docker_api, auto_detect_resources, deploy_sandbox, expire_stale_sessions, get_sandbox_status, stop_sandbox, select_node, _node_usage
from .services import (
    enrolled_labs_for,
    lab_progress_for,
    mark_lab_stage_complete,
    next_lab_for,
)

logger = logging.getLogger(__name__)


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _is_instructor(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.groups.filter(name__iexact="Instructor").exists())


def _build_admin_context(current_user_id=None):
    users = User.objects.prefetch_related("groups").order_by("username")
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    labs = Lab.objects.all()
    published_labs = labs.filter(is_published=True).count()
    total_labs = labs.count()
    draft_labs = total_labs - published_labs

    running_sessions = SandboxSession.objects.filter(status=SandboxSession.RUNNING)
    active_sessions_today = SandboxSession.objects.filter(started_at__gte=today_start)

    hackers = HackPhase.objects.annotate(lab_count=Count("labs"))
    phases_data = [{"name": h.name, "count": h.lab_count} for h in hackers]

    docker_ok = False
    container_count = 0
    try:
        resp = _docker_api("/info", method="get")
        if resp:
            docker_ok = True
            container_count = resp.get("ContainersRunning", 0)
    except Exception:
        pass

    return {
        "active_nav": "users",
        "user_role_label": "Administrator",
        "create_user_form": UserManagementForm(),
        "managed_users": [
            {
                "id": managed_user.id,
                "username": managed_user.username,
                "full_name": managed_user.get_full_name() or "-",
                "email": managed_user.email or "-",
                "role": get_role_label(managed_user),
                "is_active": managed_user.is_active,
                "last_login": managed_user.last_login,
                "is_current_user": managed_user.id == current_user_id,
            }
            for managed_user in users
        ],
        "stats": {
            "total_users": users.count(),
            "admins": users.filter(is_staff=True).count(),
            "instructors": users.filter(groups__name__iexact="Instructor").distinct().count(),
            "students": users.exclude(is_staff=True).exclude(groups__name__iexact="Instructor").distinct().count(),
            "learning_paths": LearningPath.objects.count(),
            "modules": Module.objects.count(),
            "activities": Activity.objects.count(),
        },
        "lab_stats": {
            "total": total_labs,
            "published": published_labs,
            "draft": draft_labs,
        },
        "session_stats": {
            "running": running_sessions.count(),
            "today": active_sessions_today.count(),
        },
        "docker_ok": docker_ok,
        "container_count": container_count,
        "hack_phases_data": phases_data,
        "resource_profile_count": ResourceProfile.objects.count(),
        "container_image_count": ContainerImage.objects.count(),
        "node_count": DockerNode.objects.count(),
        "now": now,
    }


def home(request):
    return render(request, "home.html")


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            if request.user.is_authenticated:
                logout(request)
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}. Your account is ready.")
            return redirect("dashboard")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form, "signup_role_label": "Student"})


@login_required
def dashboard(request):
    if _is_instructor(request.user):
        return redirect("instructor_dashboard")
    return redirect("user_dashboard")


@login_required
@user_passes_test(_is_admin)
def control_panel(request):
    return render(request, "control_panel.html", _build_admin_context(request.user.id))


@login_required
@user_passes_test(_is_admin)
def create_user(request):
    if request.method != "POST":
        return redirect("control_panel")

    form = UserManagementForm(request.POST)
    if form.is_valid():
        user = form.save()
        messages.success(request, f"{get_role_label(user)} account '{user.username}' created successfully.")
        return redirect("control_panel")

    context = _build_admin_context(request.user.id)
    context["create_user_form"] = form
    return render(request, "control_panel.html", context, status=400)


@login_required
@user_passes_test(_is_admin)
def update_user_role(request, user_id):
    if request.method != "POST":
        return redirect("control_panel")

    managed_user = get_object_or_404(User, pk=user_id)
    role = request.POST.get("role")
    if role not in {"admin", "instructor", "user"}:
        messages.error(request, "Invalid role selected.")
        return redirect("control_panel")

    managed_user.is_staff = role == "admin"
    managed_user.is_superuser = role == "admin"
    managed_user.save(update_fields=["is_staff", "is_superuser"])
    assign_role(managed_user, role)
    messages.success(request, f"Updated role for '{managed_user.username}' to {get_role_label(managed_user)}.")
    return redirect("control_panel")


@login_required
@user_passes_test(_is_admin)
def toggle_user_status(request, user_id):
    if request.method != "POST":
        return redirect("control_panel")

    managed_user = get_object_or_404(User, pk=user_id)
    if managed_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("control_panel")

    managed_user.is_active = not managed_user.is_active
    managed_user.save(update_fields=["is_active"])
    state = "activated" if managed_user.is_active else "deactivated"
    messages.success(request, f"User '{managed_user.username}' was {state}.")
    return redirect("control_panel")


@login_required
@user_passes_test(_is_admin)
def delete_user(request, user_id):
    if request.method != "POST":
        return redirect("control_panel")

    managed_user = get_object_or_404(User, pk=user_id)
    if managed_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("control_panel")

    username = managed_user.username
    managed_user.delete()
    messages.success(request, f"User '{username}' was deleted.")
    return redirect("control_panel")


@login_required
def user_dashboard(request):
    expire_stale_sessions()
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    profile_form = StudentProfileImageForm(instance=profile)

    enrolled = enrolled_labs_for(request.user)
    completed_count = 0
    enrolled_with_progress = []
    lab_progress_total = 0
    lab_progress_earned = 0
    for e in enrolled:
        p = lab_progress_for(request.user, e.lab)
        if p["is_complete"]:
            completed_count += 1
            lab_progress_earned += 3
        else:
            for s in p.get("stages", []):
                if s.get("completed"):
                    lab_progress_earned += 1
        lab_progress_total += 3
        enrolled_with_progress.append({"enrollment": e, "progress": p})
    overall_percent = round((lab_progress_earned / lab_progress_total) * 100) if lab_progress_total else 0

    active_session = SandboxSession.objects.filter(
        user=request.user, status=SandboxSession.RUNNING
    ).select_related("lab").first()

    recent_actions = []
    for sub in FlagSubmission.objects.filter(user=request.user).select_related("lab")[:5]:
        recent_actions.append({
            "type": "flag" if sub.is_correct else "wrong",
            "desc": f"{'Solved' if sub.is_correct else 'Attempted'} flag for {sub.lab.title}",
            "time": sub.submitted_at,
            "url": reverse("student_lab_detail", args=[sub.lab.id]),
        })
    for ses in SandboxSession.objects.filter(user=request.user).exclude(status=SandboxSession.PENDING).select_related("lab")[:5]:
        recent_actions.append({
            "type": "sandbox_stop" if ses.status in (SandboxSession.STOPPED, SandboxSession.EXPIRED) else "sandbox_start",
            "desc": f"{'Stopped' if ses.status in (SandboxSession.STOPPED, SandboxSession.EXPIRED) else 'Started'} sandbox for {ses.lab.title}",
            "time": ses.stopped_at or ses.started_at,
            "url": reverse("student_lab_detail", args=[ses.lab.id]),
        })
    for lp in LabProgress.objects.filter(user=request.user, completed_at__isnull=False).select_related("lab")[:5]:
        recent_actions.append({
            "type": lp.stage,
            "desc": f"Completed {lp.get_stage_display()} for {lp.lab.title}",
            "time": lp.completed_at,
            "url": reverse("student_lab_detail", args=[lp.lab.id]),
        })
    recent_actions.sort(key=lambda x: x["time"], reverse=True)
    recent_actions = recent_actions[:5]

    now = timezone.now()
    week_start = now - timezone.timedelta(days=now.weekday())
    labs_this_week = SandboxSession.objects.filter(user=request.user, started_at__gte=week_start).values("lab").distinct().count()

    session_dates = SandboxSession.objects.filter(user=request.user, status=SandboxSession.STOPPED).dates("started_at", "day", order="DESC")
    streak = 0
    if session_dates:
        check_date = now.date()
        for d in session_dates:
            if d == check_date or d == check_date - timezone.timedelta(days=1):
                streak += 1
                check_date = d
            elif d < check_date - timezone.timedelta(days=1):
                break

    badges = []
    if completed_count >= 1:
        badges.append({"icon": "trophy", "label": "First Blood", "desc": "Complete your first lab"})
    if completed_count >= 3:
        badges.append({"icon": "zap", "label": "On Fire", "desc": "Complete 3 labs"})
    if completed_count >= 5:
        badges.append({"icon": "flame", "label": "Lab Machine", "desc": "Complete 5 labs"})
    if streak >= 2:
        badges.append({"icon": "calendar-check", "label": f"{streak}-Day Streak", "desc": "Active on consecutive days"})
    if labs_this_week >= 3:
        badges.append({"icon": "activity", "label": "Weekly Warrior", "desc": "Work on 3+ labs in a week"})

    next_lab_obj = next_lab_for(request.user)
    next_lab_progress = lab_progress_for(request.user, next_lab_obj) if next_lab_obj else None

    phases = HackPhase.objects.order_by("order", "name")

    return render(
        request,
        "user_dashboard.html",
        {
            "active_nav": "dashboard",
            "user_role_label": "Student",
            "support_email": "support@somacloud.local",
            "profile": profile,
            "profile_form": profile_form,
            "enrolled_labs": enrolled,
            "enrolled_with_progress": enrolled_with_progress,
            "enrolled_labs_count": enrolled.count(),
            "completed_labs": completed_count,
            "overall_percent": overall_percent,
            "active_session": active_session,
            "recent_actions": recent_actions,
            "labs_this_week": labs_this_week,
            "streak": streak,
            "badges": badges,
            "phases": phases,
            "next_lab": next_lab_obj,
            "next_lab_progress": next_lab_progress,
            "now": now,
        },
    )


@login_required
def student_recent_activity(request):
    actions = []
    for sub in FlagSubmission.objects.filter(user=request.user).select_related("lab")[:20]:
        actions.append({
            "type": "flag" if sub.is_correct else "wrong",
            "desc": f"{'Solved' if sub.is_correct else 'Attempted'} flag for {sub.lab.title}",
            "time": sub.submitted_at,
            "lab": sub.lab,
            "detail": sub.submitted_flag[:60],
        })
    for ses in SandboxSession.objects.filter(user=request.user).exclude(status=SandboxSession.PENDING).select_related("lab")[:20]:
        actions.append({
            "type": "sandbox_stop" if ses.status in (SandboxSession.STOPPED, SandboxSession.EXPIRED) else "sandbox_start",
            "desc": f"{'Stopped' if ses.status in (SandboxSession.STOPPED, SandboxSession.EXPIRED) else 'Started'} sandbox for {ses.lab.title}",
            "time": ses.stopped_at or ses.started_at,
            "lab": ses.lab,
            "detail": ses.get_status_display(),
        })
    for lp in LabProgress.objects.filter(user=request.user, completed_at__isnull=False).select_related("lab")[:20]:
        actions.append({
            "type": lp.stage,
            "desc": f"Completed {lp.get_stage_display()} for {lp.lab.title}",
            "time": lp.completed_at,
            "lab": lp.lab,
            "detail": "",
        })
    actions.sort(key=lambda x: x["time"], reverse=True)

    return render(
        request,
        "student_recent_activity.html",
        {
            "active_nav": "activity",
            "user_role_label": "Student",
            "actions": actions,
        },
    )


@login_required
def update_student_profile_image(request):
    if request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name__iexact="Instructor").exists():
        messages.error(request, "Only student accounts can update a student profile image.")
        return redirect("dashboard")

    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method != "POST":
        return redirect("user_dashboard")

    form = StudentProfileImageForm(request.POST, request.FILES, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile image updated successfully.")
    else:
        messages.error(request, "Please upload a valid image file.")
    return redirect("user_dashboard")


@login_required
def instructor_dashboard(request):
    labs = Lab.objects.all().select_related("hack_phase", "resource_profile", "instructor").order_by("-created_at")
    total_enrollments = LabEnrollment.objects.filter(is_active=True).count()
    total_students = User.objects.exclude(is_staff=True).exclude(groups__name__iexact="Instructor").count()

    active_sessions_total = 0
    for lab in labs:
        lab.active_count = SandboxSession.objects.filter(lab=lab, status=SandboxSession.RUNNING).count()
        active_sessions_total += lab.active_count

    return render(
        request,
        "instructor_dashboard.html",
        {
            "active_nav": "dashboard",
            "user_role_label": "Instructor",
            "support_email": "support@somacloud.local",
            "labs": labs,
            "lab_count": labs.count(),
            "total_students": total_students,
            "total_enrollments": total_enrollments,
            "hack_phases": HackPhase.objects.all(),
            "resource_profiles": ResourceProfile.objects.all(),
            "active_sessions_total": active_sessions_total,
        },
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_resource_profiles(request):
    profiles = ResourceProfile.objects.all()
    return render(
        request,
        "resource_profiles.html",
        {
            "active_nav": "resources",
            "user_role_label": "Instructor",
            "profiles": profiles,
        },
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_resource_profile_create(request):
    if request.method == "POST":
        form = ResourceProfileForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource profile created successfully.")
            return redirect("instructor_resource_profiles")
    else:
        form = ResourceProfileForm()
    return render(
        request,
        "resource_profile_form.html",
        {"active_nav": "resources", "user_role_label": "Instructor", "form": form, "form_title": "Create Resource Profile"},
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_resource_profile_edit(request, profile_id):
    profile = get_object_or_404(ResourceProfile, pk=profile_id)
    if request.method == "POST":
        form = ResourceProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Resource profile '{profile.name}' updated.")
            return redirect("instructor_resource_profiles")
    else:
        form = ResourceProfileForm(instance=profile)
    return render(
        request,
        "resource_profile_form.html",
        {"active_nav": "resources", "user_role_label": "Instructor", "form": form, "form_title": f"Edit: {profile.name}", "profile": profile},
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_resource_profile_delete(request, profile_id):
    if request.method != "POST":
        return redirect("instructor_resource_profiles")
    profile = get_object_or_404(ResourceProfile, pk=profile_id)
    name = profile.name
    try:
        profile.delete()
        messages.success(request, f"Resource profile '{name}' deleted.")
    except ProtectedError:
        messages.error(request, f"Cannot delete '{name}' — it is assigned to one or more labs or activities.")
    return redirect("instructor_resource_profiles")


@login_required
def instructor_lab_create(request):
    if not _is_instructor(request.user):
        messages.error(request, "Only instructors can create labs.")
        return redirect("dashboard")

    if request.method == "POST":
        form = LabForm(request.POST)
        if form.is_valid():
            lab = form.save(commit=False)
            lab.instructor = request.user
            lab.save()
            form.save_m2m()
            messages.success(request, f"Lab '{lab.title}' created successfully.")
            return redirect("instructor_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LabForm()

    return render(
        request,
        "instructor_lab_form.html",
        {
            "active_nav": "labs",
            "user_role_label": "Instructor",
            "form": form,
            "form_title": "Create Lab",
        },
    )


@login_required
def instructor_lab_edit(request, lab_id):
    lab = get_object_or_404(Lab, pk=lab_id) if request.user.is_staff or request.user.is_superuser else get_object_or_404(Lab, pk=lab_id, instructor=request.user)

    if request.method == "POST":
        form = LabForm(request.POST, instance=lab)
        if form.is_valid():
            form.save()
            messages.success(request, f"Lab '{lab.title}' updated.")
            return redirect("instructor_dashboard")
    else:
        form = LabForm(instance=lab)

    return render(
        request,
        "instructor_lab_form.html",
        {
            "active_nav": "labs",
            "user_role_label": "Instructor",
            "form": form,
            "form_title": f"Edit: {lab.title}",
            "lab": lab,
        },
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_live_monitor(request):
    expire_stale_sessions()
    sessions = SandboxSession.objects.filter(status=SandboxSession.RUNNING).select_related("user", "lab", "node").order_by("-started_at")

    total_online = sessions.count()
    lab_breakdown = {}
    node_breakdown = {}
    for s in sessions:
        lab_breakdown[s.lab.title] = lab_breakdown.get(s.lab.title, 0) + 1
        node_name = s.node.name if s.node else "unknown"
        node_breakdown[node_name] = node_breakdown.get(node_name, 0) + 1

    return render(
        request,
        "instructor_live_monitor.html",
        {
            "active_nav": "monitor",
            "user_role_label": "Instructor",
            "sessions": sessions,
            "total_online": total_online,
            "lab_breakdown": lab_breakdown,
            "node_breakdown": node_breakdown,
            "now": timezone.now(),
        },
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_student_analytics(request, user_id=None):
    if user_id is None:
        students = User.objects.filter(groups__name__iexact="Instructor").exclude(pk__in=[]) | User.objects.filter(is_staff=False, is_superuser=False)
        students = students.exclude(groups__name__iexact="Instructor").exclude(is_staff=True).exclude(is_superuser=True).order_by("username")
        return render(
            request,
            "instructor_student_analytics.html",
            {
                "active_nav": "analytics",
                "user_role_label": "Instructor",
                "students": students,
                "is_list_view": True,
            },
        )

    student = get_object_or_404(User, pk=user_id)
    sessions = SandboxSession.objects.filter(user=student).select_related("lab").order_by("-started_at")
    progress = LabProgress.objects.filter(user=student).select_related("lab").order_by("-completed_at")
    submissions = FlagSubmission.objects.filter(user=student).select_related("lab").order_by("-submitted_at")

    total_labs = LabEnrollment.objects.filter(user=student, is_active=True).count()
    completed_labs = LabProgress.objects.filter(user=student, stage=LabProgress.COMPLETE, completed_at__isnull=False).count()
    total_sessions = sessions.count()
    running_sessions = sessions.filter(status=SandboxSession.RUNNING).count()
    flag_solved = submissions.filter(is_correct=True).values("lab").distinct().count()

    timeline = []
    for s in sessions:
        timeline.append({
            "type": "session",
            "icon": "server",
            "label": f"Sandbox {'started' if s.status == SandboxSession.RUNNING else s.status}",
            "detail": s.lab.title,
            "time": s.started_at,
        })
    for p in progress:
        if p.completed_at:
            timeline.append({
                "type": "progress",
                "icon": "check-circle",
                "label": f"{p.get_stage_display()} completed",
                "detail": p.lab.title,
                "time": p.completed_at,
            })
    for sub in submissions:
        timeline.append({
            "type": "flag",
            "icon": "flag" if sub.is_correct else "x-circle",
            "label": f"Flag {'correct' if sub.is_correct else 'incorrect'}",
            "detail": f"{sub.lab.title}: {sub.submitted_flag[:40]}",
            "time": sub.submitted_at,
        })
    timeline.sort(key=lambda x: x["time"], reverse=True)

    return render(
        request,
        "instructor_student_analytics.html",
        {
            "active_nav": "analytics",
            "user_role_label": "Instructor",
            "student": student,
            "sessions": sessions,
            "progress": progress,
            "submissions": submissions,
            "total_labs": total_labs,
            "completed_labs": completed_labs,
            "total_sessions": total_sessions,
            "running_sessions": running_sessions,
            "flag_solved": flag_solved,
            "timeline": timeline,
            "now": timezone.now(),
        },
    )


@login_required
@user_passes_test(_is_instructor)
def analytics_chart_progress(request, user_id):
    student = get_object_or_404(User, pk=user_id)
    progress = LabProgress.objects.filter(user=student, completed_at__isnull=False).select_related("lab")

    stages_count = {"Theory": 0, "Sandbox": 0, "Challenge": 0, "Complete": 0}
    for p in progress:
        name = p.get_stage_display()
        stages_count[name] = stages_count.get(name, 0) + 1

    fig, ax = plt.subplots(figsize=(5, 3))
    stages = list(stages_count.keys())
    counts = list(stages_count.values())
    colors = ["#0067c0", "#107c41", "#d99322", "#5c5c5c"]
    bars = ax.bar(stages, counts, color=colors[:len(stages)])
    ax.set_ylabel("Labs")
    ax.set_title("Progress by Stage", fontsize=11, fontweight="semibold")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, str(count),
                ha="center", va="bottom", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    from django.http import HttpResponse
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
@user_passes_test(_is_instructor)
def analytics_chart_sessions(request, user_id):
    student = get_object_or_404(User, pk=user_id)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    sessions = SandboxSession.objects.filter(user=student, started_at__gte=thirty_days_ago)

    daily = {}
    for s in sessions:
        day = s.started_at.strftime("%b %d")
        daily[day] = daily.get(day, 0) + 1

    fig, ax = plt.subplots(figsize=(5, 3))
    days = list(daily.keys())
    counts = list(daily.values())
    if days:
        ax.fill_between(range(len(days)), counts, alpha=0.3, color="#0067c0")
        ax.plot(range(len(days)), counts, color="#0067c0", linewidth=2, marker="o", markersize=4)
        ax.set_xticks(range(len(days)))
        ax.set_xticklabels(days, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Sessions")
    ax.set_title("Session Activity (30 days)", fontsize=11, fontweight="semibold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    from django.http import HttpResponse
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
@user_passes_test(_is_instructor)
def instructor_lab_sessions(request, lab_id):
    lab = get_object_or_404(Lab, pk=lab_id) if request.user.is_staff or request.user.is_superuser else get_object_or_404(Lab, pk=lab_id, instructor=request.user)
    sessions = SandboxSession.objects.filter(lab=lab).select_related("user").order_by("-started_at")

    return render(
        request,
        "instructor_lab_sessions.html",
        {
            "active_nav": "dashboard",
            "user_role_label": "Instructor",
            "lab": lab,
            "sessions": sessions,
            "now": timezone.now(),
        },
    )


@login_required
def instructor_lab_toggle(request, lab_id):
    if request.method != "POST":
        return redirect("instructor_dashboard")
    if request.user.is_staff or request.user.is_superuser:
        lab = get_object_or_404(Lab, pk=lab_id)
    else:
        lab = get_object_or_404(Lab, pk=lab_id, instructor=request.user)
    lab.is_published = not lab.is_published
    lab.save(update_fields=["is_published"])
    state = "published" if lab.is_published else "unpublished"
    messages.success(request, f"Lab '{lab.title}' was {state}.")
    return redirect("instructor_dashboard")


@login_required
def instructor_lab_delete(request, lab_id):
    if request.method != "POST":
        return redirect("instructor_dashboard")
    if request.user.is_staff or request.user.is_superuser:
        lab = get_object_or_404(Lab, pk=lab_id)
    else:
        lab = get_object_or_404(Lab, pk=lab_id, instructor=request.user)
    title = lab.title
    lab.delete()
    messages.success(request, f"Lab '{title}' was deleted.")
    return redirect("instructor_dashboard")


@login_required
def student_labs(request):
    phases = HackPhase.objects.prefetch_related("labs").filter(labs__is_published=True).distinct().order_by("order", "name")
    enrolled_ids = set(LabEnrollment.objects.filter(user=request.user, is_active=True).values_list("lab_id", flat=True))

    return render(
        request,
        "student_labs.html",
        {
            "active_nav": "labs",
            "user_role_label": "Student",
            "phases": phases,
            "enrolled_ids": enrolled_ids,
        },
    )


@login_required
def student_enroll_lab(request, lab_id):
    if request.method != "POST":
        return redirect("student_labs")
    lab = get_object_or_404(Lab, pk=lab_id, is_published=True)
    _, created = LabEnrollment.objects.get_or_create(user=request.user, lab=lab)
    if created:
        messages.success(request, f"Enrolled in lab '{lab.title}'.")
    else:
        messages.info(request, f"You are already enrolled in '{lab.title}'.")
    return redirect("student_lab_detail", lab_id=lab.id)


@login_required
def student_lab_detail(request, lab_id):
    lab = get_object_or_404(
        Lab.objects.select_related("hack_phase", "resource_profile", "terminal_container").prefetch_related("tools", "service_containers"),
        pk=lab_id,
    )
    get_object_or_404(LabEnrollment, user=request.user, lab=lab, is_active=True)

    progress = lab_progress_for(request.user, lab)
    active_session = SandboxSession.objects.filter(
        user=request.user, lab=lab, status__in=[SandboxSession.PENDING, SandboxSession.RUNNING]
    ).first()

    html_content = ""
    if lab.theory_content:
        html_content = render_markdown(lab.theory_content)

    last_submission = FlagSubmission.objects.filter(user=request.user, lab=lab).order_by("-submitted_at").first()
    recent_correct = FlagSubmission.objects.filter(user=request.user, lab=lab, is_correct=True).exists()

    return render(
        request,
        "student_lab_detail.html",
        {
            "active_nav": "labs",
            "user_role_label": "Student",
            "lab": lab,
            "progress": progress,
            "active_session": active_session,
            "html_content": html_content,
            "last_submission": last_submission,
            "recent_correct": recent_correct,
        },
    )


@login_required
def student_complete_theory(request, lab_id):
    if request.method != "POST":
        return redirect("student_labs")
    lab = get_object_or_404(Lab, pk=lab_id)
    get_object_or_404(LabEnrollment, user=request.user, lab=lab, is_active=True)
    mark_lab_stage_complete(request.user, lab, LabProgress.THEORY)
    messages.success(request, f"Theory for '{lab.title}' marked complete.")
    return redirect("student_lab_detail", lab_id=lab.id)


@login_required
def submit_flag(request, lab_id):
    if request.method != "POST":
        return redirect("student_labs")
    lab = get_object_or_404(Lab, pk=lab_id)
    get_object_or_404(LabEnrollment, user=request.user, lab=lab, is_active=True)

    if lab.challenge_type == "question":
        submitted = request.POST.get("answer", "").strip()
        if not submitted:
            messages.error(request, "Please provide an answer.")
            return redirect("student_lab_detail", lab_id=lab.id)
        is_correct = submitted == lab.challenge_answer
        FlagSubmission.objects.create(user=request.user, lab=lab, submitted_flag=submitted, is_correct=is_correct)
    else:
        submitted = request.POST.get("flag", "").strip()
        if not submitted:
            messages.error(request, "Please enter a flag.")
            return redirect("student_lab_detail", lab_id=lab.id)
        is_correct = submitted == lab.flag
        FlagSubmission.objects.create(user=request.user, lab=lab, submitted_flag=submitted, is_correct=is_correct)

    if is_correct:
        mark_lab_stage_complete(request.user, lab, LabProgress.CHALLENGE)
        mark_lab_stage_complete(request.user, lab, LabProgress.COMPLETE)
        active = SandboxSession.objects.filter(
            user=request.user, lab=lab, status__in=[SandboxSession.PENDING, SandboxSession.RUNNING]
        ).first()
        if active:
            stop_sandbox(active)
        messages.success(request, f"Correct! Lab '{lab.title}' completed.")
    else:
        hint = lab.flag_hint or "Incorrect. Try again."
        messages.error(request, f"Incorrect. {hint}")

    return redirect("student_lab_detail", lab_id=lab.id)


@login_required
def launch_sandbox(request, lab_id):
    if request.method != "POST":
        return redirect("student_labs")
    lab = get_object_or_404(Lab.objects.select_related("resource_profile"), pk=lab_id)
    get_object_or_404(LabEnrollment, user=request.user, lab=lab, is_active=True)

    with transaction.atomic():
        active = SandboxSession.objects.select_for_update().filter(
            user=request.user, lab=lab, status__in=[SandboxSession.PENDING, SandboxSession.RUNNING]
        ).first()
        if active:
            messages.warning(request, "You already have an active sandbox session.")
            return redirect("student_sandbox_view", session_id=active.id)

        session = SandboxSession.objects.create(
            user=request.user,
            lab=lab,
            expires_at=timezone.now() + timedelta(minutes=lab.resource_profile.time_limit_minutes),
        )

    result = deploy_sandbox(session)
    if not result:
        messages.error(request, "Failed to launch sandbox. Check server connection.")
        return redirect("student_lab_detail", lab_id=lab.id)

    messages.success(request, "Sandbox launched successfully!")
    return redirect("student_sandbox_view", session_id=session.id)


@login_required
def student_sandbox_view(request, session_id):
    expire_stale_sessions()
    session = get_object_or_404(SandboxSession, pk=session_id, user=request.user)
    status = get_sandbox_status(session)
    remaining = None
    if session.expires_at and status == SandboxSession.RUNNING:
        delta = session.expires_at - timezone.now()
        remaining = max(0, int(delta.total_seconds()))

    notes = session.lab.notes or ""
    if notes:
        endpoints = ", ".join(
            f"{item['name']} ({item['ip']}:{item['container_port']})"
            for item in session.service_endpoints
        )
        notes = notes.replace("{{SERVICE_IP}}", session.service_ip or "[no target configured]")
        notes = notes.replace("{{SERVICE_ENDPOINTS}}", endpoints or "[no targets configured]")

    return render(
        request,
        "student_sandbox.html",
        {
            "active_nav": "labs",
            "user_role_label": "Student",
            "session": session,
            "status": status,
            "remaining": remaining,
            "progress": lab_progress_for(request.user, session.lab),
            "sandbox_notes": render_markdown(notes) if notes else "",
        },
    )


@login_required
def stop_sandbox_session(request, session_id):
    if request.method != "POST":
        return redirect("student_labs")
    session = get_object_or_404(SandboxSession, pk=session_id, user=request.user)
    stop_sandbox(session)
    mark_lab_stage_complete(request.user, session.lab, LabProgress.SANDBOX)
    progress = lab_progress_for(request.user, session.lab)
    if progress["is_complete"]:
        mark_lab_stage_complete(request.user, session.lab, LabProgress.COMPLETE)
        messages.success(request, f"Lab '{session.lab.title}' completed!")
    else:
        messages.success(request, "Sandbox stopped. Complete the theory stage to finish the lab.")
    return redirect("student_lab_detail", lab_id=session.lab.id)


@login_required
def sandbox_session_status(request, session_id):
    expire_stale_sessions()
    session = get_object_or_404(SandboxSession, pk=session_id, user=request.user)
    status = get_sandbox_status(session)
    remaining = None
    if session.expires_at and status == SandboxSession.RUNNING:
        delta = session.expires_at - timezone.now()
        remaining = max(0, int(delta.total_seconds()))
    return JsonResponse({
        "status": status,
        "remaining": remaining,
        "terminal_url": session.terminal_url if status == SandboxSession.RUNNING else "",
    })


@login_required
def student_profile(request):
    role_label = get_role_label(request.user)
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    password_error = None

    if request.method == "POST":
        if "update_profile" in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated.")
                return redirect("student_profile")
        elif "change_password" in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed.")
                return redirect("student_profile")
            else:
                password_error = password_form.errors.get("__all__", []) or [str(e) for errors in password_form.errors.values() for e in errors]

    return render(
        request,
        "student_profile.html",
        {
            "active_nav": "profile",
            "user_role_label": role_label,
            "profile_form": profile_form,
            "password_form": password_form,
            "password_error": password_error,
        },
    )


# ---------------------------------------------------------------------------
# Docker Node Management (admin only)
# ---------------------------------------------------------------------------

@login_required
def node_list(request):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    nodes = list(DockerNode.objects.all())
    active_count = sum(1 for n in nodes if n.status == DockerNode.ACTIVE)
    total_sessions = sum(n.current_sessions for n in nodes)
    for node in nodes:
        used_cpu, used_mem = _node_usage(node)
        total_cpu = float(node.total_cpu) if node.total_cpu else 0
        total_mem = node.total_memory_mb or 0
        node.cpu_used = used_cpu
        node.cpu_percent = round((used_cpu / total_cpu * 100) if total_cpu > 0 else 0)
        node.mem_used = used_mem
        node.mem_percent = round((used_mem / total_mem * 100) if total_mem > 0 else 0)
    return render(
        request,
        "node_list.html",
        {
            "active_nav": "nodes",
            "user_role_label": get_role_label(request.user),
            "nodes": nodes,
            "active_count": active_count,
            "total_sessions": total_sessions,
            "add_form": DockerNodeForm(),
        },
    )


@login_required
def node_detail(request, node_id):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    node = get_object_or_404(DockerNode, pk=node_id)
    used_cpu, used_mem = _node_usage(node)
    total_cpu = float(node.total_cpu) if node.total_cpu else 0
    total_mem = node.total_memory_mb or 0
    node.cpu_used = used_cpu
    node.cpu_percent = round((used_cpu / total_cpu * 100) if total_cpu > 0 else 0)
    node.mem_used = used_mem
    node.mem_percent = round((used_mem / total_mem * 100) if total_mem > 0 else 0)
    sessions = SandboxSession.objects.filter(node=node, status=SandboxSession.RUNNING).select_related("user", "lab")
    return render(
        request,
        "node_detail.html",
        {
            "active_nav": "nodes",
            "user_role_label": get_role_label(request.user),
            "node": node,
            "sessions": sessions,
        },
    )


@login_required
def node_add(request):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    if request.method != "POST":
        return redirect("node_list")
    form = DockerNodeForm(request.POST)
    if form.is_valid():
        node = form.save(commit=False)
        if not node.ssh_host:
            node.ssh_host = node.public_ip
        if not node.docker_host:
            node.docker_host = f"https://{node.public_ip}:2376"
        node.save()
        messages.success(request, f"Node '{node.name}' registered. Use 'Setup Node' to configure it remotely.")
        return redirect("node_list")
    nodes = DockerNode.objects.all()
    active_count = nodes.filter(status=DockerNode.ACTIVE).count()
    total_sessions = sum(n.current_sessions for n in nodes)
    return render(
        request,
        "node_list.html",
        {
            "active_nav": "nodes",
            "user_role_label": get_role_label(request.user),
            "nodes": nodes,
            "active_count": active_count,
            "total_sessions": total_sessions,
            "add_form": form,
            "show_add_form": True,
        },
    )


@login_required
def node_delete(request, node_id):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    if request.method != "POST":
        return redirect("node_list")
    node = get_object_or_404(DockerNode, pk=node_id)
    if node.current_sessions > 0:
        messages.error(request, f"Cannot delete '{node.name}' — it has {node.current_sessions} active session(s). Drain it first.")
        return redirect("node_list")
    name = node.name
    node.delete()
    messages.success(request, f"Node '{name}' deleted.")
    return redirect("node_list")


@login_required
def node_toggle(request, node_id):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    if request.method != "POST":
        return redirect("node_list")
    node = get_object_or_404(DockerNode, pk=node_id)
    if node.status == DockerNode.ACTIVE:
        if node.current_sessions > 0:
            messages.warning(
                request,
                f"Node '{node.name}' has {node.current_sessions} active session(s). "
                f"They will be orphaned when the EC2 instance is stopped. "
                f"Use 'Drain' first to let them finish, or confirm deactivation.",
            )
        node.status = DockerNode.OFFLINE
        messages.success(request, f"Node '{node.name}' deactivated. No new sessions will be placed here.")
    else:
        node.status = DockerNode.ACTIVE
        messages.success(request, f"Node '{node.name}' reactivated.")
    node.save(update_fields=["status"])
    return redirect("node_list")


@login_required
def node_health(request, node_id):
    if not _is_admin(request.user):
        return JsonResponse({"error": "access denied"}, status=403)
    node = get_object_or_404(DockerNode, pk=node_id)
    result = _docker_api("/_ping", method="get", timeout=5, node=node)
    if result is not None:
        node.status = DockerNode.ACTIVE
        node.last_health_check = timezone.now()
        node.save(update_fields=["status", "last_health_check"])
        auto_detect_resources(node)
        return JsonResponse({
            "status": "ok",
            "node": node.name,
            "cpu": str(node.total_cpu),
            "memory_mb": node.total_memory_mb,
        })
    else:
        node.status = DockerNode.OFFLINE
        node.last_health_check = timezone.now()
        node.save(update_fields=["status", "last_health_check"])
        return JsonResponse({"status": "offline", "node": node.name})


@login_required
def node_health_all(request):
    if not _is_admin(request.user):
        return redirect("dashboard")
    nodes = DockerNode.objects.all()
    checked = 0
    for node in nodes:
        result = _docker_api("/_ping", method="get", timeout=5, node=node)
        if result is not None:
            node.status = DockerNode.ACTIVE
            auto_detect_resources(node)
        else:
            node.status = DockerNode.OFFLINE
        node.last_health_check = timezone.now()
        node.save(update_fields=["status", "last_health_check"])
        checked += 1
    messages.success(request, f"Health check completed for {checked} node(s). Resources auto-detected.")
    return redirect("node_list")


# ---------------------------------------------------------------------------
# Node SSH Setup (Phase 2)
# ---------------------------------------------------------------------------

def _build_setup_script(node, setup_token):
    """Generate a bash script that installs Docker + TLS on a worker node."""
    from django.conf import settings

    ca_cert = ca.get_ca_cert_pem().decode()
    app_url = settings.APP_SERVER_URL.rstrip("/")
    swarm_token_url = f"{app_url}/admin/nodes/{node.id}/ca/token/{setup_token}/"
    sign_url = f"{app_url}/admin/nodes/{node.id}/ca/sign/{setup_token}/"
    callback_url = f"{app_url}/admin/nodes/{node.id}/setup-complete/{setup_token}/"

    return f"""#!/bin/bash
set -euo pipefail

NODE_NAME="{node.name}"
NODE_IP="{node.public_ip}"
PORT_START="{node.port_start}"
PORT_END="{node.port_end}"
SIGN_URL="{sign_url}"
TOKEN_URL="{swarm_token_url}"
CALLBACK_URL="{callback_url}"
CA_CERT_PEM='{ca_cert}'

echo "[1/7] Detecting OS..."
if command -v docker &>/dev/null; then
    echo "Docker already installed, skipping install."
else
    echo "Installing Docker..."
    if [ -f /etc/debian_version ]; then
        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io
    elif [ -f /etc/redhat-release ]; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io
    else
        echo "Unsupported OS. Install Docker manually."
        exit 1
    fi
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully."
fi

echo "[2/7] Generating TLS keypair..."
mkdir -p /etc/docker/tls
cd /etc/docker/tls

openssl genrsa -out server.key 2048 2>/dev/null
openssl req -new -key server.key -out server.csr \
    -subj "/CN=somacloud-worker-${{NODE_NAME}}/O=SomaCloud" 2>/dev/null

echo "[3/7] Signing certificate with CA..."
CSR=$(cat server.csr)
SIGNED_CERT=$(curl -sk -X POST "{sign_url}" \
    -H "Content-Type: application/json" \
    -d "{{\"csr\": \"$(echo "$CSR" | tr '\\n' '~')}}")
# Replace newlines
SIGNED_CERT=$(echo "$SIGNED_CERT" | sed 's/~/\\n/g; s/^"//; s/"$//')

if [ -z "$SIGNED_CERT" ] || [ "$SIGNED_CERT" = "null" ]; then
    echo "ERROR: Certificate signing failed."
    exit 1
fi

echo "$SIGNED_CERT" > server.crt
echo "$CA_CERT_PEM" > ca.pem
rm -f server.csr
echo "Certificates installed."

echo "[4/7] Configuring Docker daemon..."
cat > /etc/docker/daemon.json <<DAEMON
{{
    "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
    "tls": true,
    "tlsverify": true,
    "tlscacert": "/etc/docker/tls/ca.pem",
    "tlscert": "/etc/docker/tls/server.crt",
    "tlskey": "/etc/docker/tls/server.key"
}}
DAEMON

# Add systemd override to avoid conflicts with ExecStart
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF

systemctl daemon-reload
systemctl restart docker
echo "Docker daemon configured and restarted."

echo "[5/7] Waiting for Docker to start..."
sleep 3
docker info >/dev/null 2>&1 || (sleep 5 && docker info >/dev/null 2>&1)
echo "Docker is responsive."

echo "[6/7] Joining Docker Swarm..."
JOIN_TOKEN=$(curl -sk "{token_url}")
JOIN_TOKEN=$(echo "$JOIN_TOKEN" | sed 's/^"//; s/"$//')
if [ -z "$JOIN_TOKEN" ] || [ "$JOIN_TOKEN" = "null" ]; then
    echo "ERROR: Could not retrieve swarm join token."
    exit 1
fi
docker swarm join --token "$JOIN_TOKEN" {settings.SWARM_MANAGER_IP}:2377 || echo "Already in swarm or join failed (continuing)."

echo "[7/7] Notifying app server..."
curl -sk -X POST "{callback_url}" -H "Content-Type: application/json"

echo ""
echo "=== Setup complete for ${{NODE_NAME}} ==="
"""


@login_required
def node_setup(request, node_id):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    node = get_object_or_404(DockerNode, pk=node_id)

    if request.method == "POST":
        import paramiko
        import io

        if not node.ssh_key or not node.ssh_key.private_key:
            messages.error(request, f"No SSH key assigned to '{node.name}'. Edit the node and select an SSH key first.")
            return redirect("node_list")

        # Read the pre-registered key
        try:
            key_data = node.ssh_key.private_key.open("rb").read()
        except Exception as exc:
            messages.error(request, f"Could not read SSH key file: {exc}")
            return redirect("node_list")

        ssh_passphrase = request.POST.get("ssh_passphrase", "") or None

        try:
            pkey = paramiko.Ed25519Key.from_private_key(io.BytesIO(key_data), password=ssh_passphrase)
        except Exception:
            try:
                pkey = paramiko.RSAKey.from_private_key(io.BytesIO(key_data), password=ssh_passphrase)
            except Exception:
                try:
                    pkey = paramiko.ECDSAKey.from_private_key(io.BytesIO(key_data), password=ssh_passphrase)
                except Exception:
                    messages.error(request, "Could not parse SSH key. Ensure it's a valid Ed25519, RSA, or ECDSA key.")
                    return redirect("node_list")

        # Generate setup token
        token = uuid.uuid4().hex
        node.setup_token = token
        node.setup_token_expires = timezone.now() + timezone.timedelta(minutes=30)
        node.save(update_fields=["setup_token", "setup_token_expires"])

        # Build script
        script = _build_setup_script(node, token)

        # Connect via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": node.ssh_host or node.public_ip,
            "port": node.ssh_port,
            "username": node.ssh_user,
            "pkey": pkey,
            "timeout": 15,
        }

        try:
            ssh.connect(**connect_kwargs)
        except Exception as exc:
            messages.error(request, f"SSH connection failed: {exc}")
            return redirect("node_list")

        # Execute setup script
        try:
            stdin, stdout, stderr = ssh.exec_command("bash -s", timeout=600)
            stdin.write(script)
            stdin.channel.shutdown_write()
            output = stdout.read().decode(errors="replace")
            errors = stderr.read().decode(errors="replace")
            exit_code = stdout.channel.recv_exit_status()
        except Exception as exc:
            messages.error(request, f"Setup script execution failed: {exc}")
            ssh.close()
            return redirect("node_list")
        finally:
            ssh.close()

        # Generate client cert for the app server to talk to this worker
        try:
            ca.generate_client_cert(node.name)
        except Exception as exc:
            logger.warning("Client cert generation failed for %s: %s", node.name, exc)

        if exit_code == 0:
            messages.success(request, f"Node '{node.name}' setup completed successfully!")
        else:
            messages.warning(request, f"Node '{node.name}' setup finished with exit code {exit_code}. Check output.")
            logger.error("Setup output for %s:\n%s\nSTDERR:\n%s", node.name, output, errors)

        return redirect("node_list")

    return render(request, "node_setup.html", {
        "active_nav": "nodes",
        "user_role_label": get_role_label(request.user),
        "node": node,
    })


# ---------------------------------------------------------------------------
# CA endpoints (called by worker setup scripts, token-authenticated)
# ---------------------------------------------------------------------------

def _verify_setup_token(request, node_id, token):
    """Verify setup token and return the node, or None."""
    node = DockerNode.objects.filter(pk=node_id, setup_token=token).first()
    if not node or not node.setup_token_expires:
        return None
    if timezone.now() > node.setup_token_expires:
        return None
    return node


@csrf_exempt
def node_ca_sign(request, node_id, token):
    """Sign a CSR submitted by a worker during setup."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    node = _verify_setup_token(request, node_id, token)
    if not node:
        return JsonResponse({"error": "invalid or expired token"}, status=403)

    try:
        body = json.loads(request.body)
        csr_pem = body.get("csr", "").replace("~", "\n").encode()
        signed_cert = ca.sign_csr(csr_pem)
        return JsonResponse({"cert": signed_cert.decode()})
    except Exception as exc:
        logger.error("CSR signing failed for %s: %s", node.name, exc)
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
def node_swarm_token(request, node_id, token):
    """Return the swarm join token for a worker."""
    node = _verify_setup_token(request, node_id, token)
    if not node:
        return JsonResponse({"error": "invalid or expired token"}, status=403)

    try:
        resp = _docker_api("/swarm/inspect", method="get")
        if resp:
            join_token = resp.get("JoinTokens", {}).get("Worker", "")
            return JsonResponse({"token": join_token})
    except Exception:
        pass
    return JsonResponse({"error": "could not retrieve swarm token"}, status=500)


@csrf_exempt
def node_setup_complete(request, node_id, token):
    """Called by the worker script after setup is done."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    node = _verify_setup_token(request, node_id, token)
    if not node:
        return JsonResponse({"error": "invalid or expired token"}, status=403)

    node.status = DockerNode.ACTIVE
    node.setup_token = ""
    node.setup_token_expires = None
    node.last_health_check = timezone.now()
    node.save(update_fields=["status", "setup_token", "setup_token_expires", "last_health_check"])
    logger.info("Node '%s' setup completed, marked active.", node.name)
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# SSH Key Management (admin only)
# ---------------------------------------------------------------------------

@login_required
def sshkey_list(request):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    keys = SSHKey.objects.select_related("uploaded_by").all()
    upload_form = SSHKeyUploadForm()
    return render(request, "sshkey_list.html", {
        "active_nav": "sshkeys",
        "user_role_label": get_role_label(request.user),
        "keys": keys,
        "upload_form": upload_form,
    })


@login_required
def sshkey_upload(request):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    if request.method != "POST":
        return redirect("sshkey_list")
    form = SSHKeyUploadForm(request.POST, request.FILES)
    if form.is_valid():
        key = form.save(commit=False)
        key.uploaded_by = request.user
        key.save()
        messages.success(request, f"SSH key '{key.name}' uploaded. Fingerprint: {key.fingerprint}")
        return redirect("sshkey_list")
    keys = SSHKey.objects.select_related("uploaded_by").all()
    return render(request, "sshkey_list.html", {
        "active_nav": "sshkeys",
        "user_role_label": get_role_label(request.user),
        "keys": keys,
        "upload_form": form,
        "show_upload": True,
    })


@login_required
def sshkey_delete(request, key_id):
    if not _is_admin(request.user):
        messages.error(request, "Access denied.")
        return redirect("dashboard")
    if request.method != "POST":
        return redirect("sshkey_list")
    key = get_object_or_404(SSHKey, pk=key_id)
    if DockerNode.objects.filter(ssh_key=key).exists():
        messages.error(request, f"Cannot delete '{key.name}' — it is assigned to one or more nodes. Remove the assignment first.")
        return redirect("sshkey_list")
    name = key.name
    key.private_key.delete(save=False)
    key.delete()
    messages.success(request, f"SSH key '{name}' deleted.")
    return redirect("sshkey_list")
