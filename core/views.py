import json
import logging

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db.models import Count, Q, ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .content_loader import render_markdown
from .forms import (
    LabForm,
    ResourceProfileForm,
    SignUpForm,
    StudentProfileImageForm,
    UserManagementForm,
    UserProfileForm,
    assign_role,
    get_role_label,
)
from .models import (
    Activity,
    ContainerImage,
    FlagSubmission,
    HackPhase,
    Lab,
    LabEnrollment,
    LabProgress,
    LearningPath,
    Module,
    ResourceProfile,
    SandboxSession,
    StudentProfile,
    Tool,
)
from .orchestrator import _docker_api, deploy_sandbox, get_sandbox_status, stop_sandbox
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
    if request.user.is_staff or request.user.is_superuser:
        return redirect("control_panel")
    if request.user.groups.filter(name__iexact="Instructor").exists():
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
            "next_lab": next_lab_obj,
            "next_lab_progress": next_lab_progress,
            "now": now,
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
    labs = Lab.objects.filter(instructor=request.user).select_related("hack_phase", "resource_profile").order_by("-created_at")
    total_students = User.objects.exclude(is_staff=True).exclude(groups__name__iexact="Instructor").count()
    total_enrollments = LabEnrollment.objects.filter(lab__instructor=request.user, is_active=True).count()

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
    lab = get_object_or_404(Lab, pk=lab_id, instructor=request.user)

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
    if request.user.is_staff or request.user.is_superuser:
        sessions = SandboxSession.objects.filter(status=SandboxSession.RUNNING).select_related("user", "lab").order_by("-started_at")
    else:
        sessions = SandboxSession.objects.filter(lab__instructor=request.user, status=SandboxSession.RUNNING).select_related("user", "lab").order_by("-started_at")

    total_online = sessions.count()
    lab_breakdown = {}
    for s in sessions:
        lab_breakdown[s.lab.title] = lab_breakdown.get(s.lab.title, 0) + 1

    return render(
        request,
        "instructor_live_monitor.html",
        {
            "active_nav": "monitor",
            "user_role_label": "Instructor",
            "sessions": sessions,
            "total_online": total_online,
            "lab_breakdown": lab_breakdown,
            "now": timezone.now(),
        },
    )


@login_required
@user_passes_test(_is_instructor)
def instructor_lab_sessions(request, lab_id):
    lab = get_object_or_404(Lab, pk=lab_id, instructor=request.user)
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

    rendered_notes = ""
    if lab.notes:
        rendered_notes = lab.notes
        if active_session and active_session.service_ip:
            rendered_notes = rendered_notes.replace("{{SERVICE_IP}}", active_session.service_ip)
            endpoints = ", ".join(
                f"{item['name']} ({item['ip']}:{item['container_port']})"
                for item in active_session.service_endpoints
            )
            rendered_notes = rendered_notes.replace("{{SERVICE_ENDPOINTS}}", endpoints)
        else:
            rendered_notes = rendered_notes.replace("{{SERVICE_IP}}", "[service IP will appear after launching sandbox]")
            rendered_notes = rendered_notes.replace("{{SERVICE_ENDPOINTS}}", "[service endpoints will appear after launching sandbox]")
        rendered_notes = render_markdown(rendered_notes)

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
            "rendered_notes": rendered_notes,
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

    active = SandboxSession.objects.filter(
        user=request.user, lab=lab, status__in=[SandboxSession.PENDING, SandboxSession.RUNNING]
    ).first()
    if active:
        messages.warning(request, "You already have an active sandbox session.")
        return redirect("student_sandbox_view", session_id=active.id)

    session = SandboxSession.objects.create(
        user=request.user,
        lab=lab,
        expires_at=timezone.now() + timezone.timedelta(minutes=lab.resource_profile.time_limit_minutes),
    )

    result = deploy_sandbox(session)
    if not result:
        messages.error(request, "Failed to launch sandbox. Check server connection.")
        return redirect("student_lab_detail", lab_id=lab.id)

    messages.success(request, "Sandbox launched successfully!")
    return redirect("student_sandbox_view", session_id=session.id)


@login_required
def student_sandbox_view(request, session_id):
    session = get_object_or_404(SandboxSession, pk=session_id, user=request.user)
    status = get_sandbox_status(session)
    remaining = None
    if session.expires_at and status == SandboxSession.RUNNING:
        delta = session.expires_at - timezone.now()
        remaining = max(0, int(delta.total_seconds()))

    return render(
        request,
        "student_sandbox.html",
        {
            "active_nav": "labs",
            "user_role_label": "Student",
            "session": session,
            "status": status,
            "remaining": remaining,
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


@login_required
def progress_overview(request):
    role_label = get_role_label(request.user)
    if role_label in {"Instructor", "Administrator"}:
        labs = Lab.objects.select_related("hack_phase", "resource_profile").order_by("hack_phase__order", "order")
        total_labs = labs.count()
        total_enrollments = LabEnrollment.objects.filter(is_active=True).count()
        completed = LabProgress.objects.filter(stage=LabProgress.COMPLETE, completed_at__isnull=False).values("user", "lab").distinct().count()

        return render(
            request,
            "progress_overview.html",
            {
                "active_nav": "progress",
                "user_role_label": role_label,
                "summary": {
                    "total_labs": total_labs,
                    "total_enrollments": total_enrollments,
                    "completed_labs": completed,
                    "published_labs": Lab.objects.filter(is_published=True).count(),
                },
                "all_labs": labs,
            },
        )

    enrolled = enrolled_labs_for(request.user)
    lab_progress_data = []
    completed_count = 0
    for e in enrolled:
        p = lab_progress_for(request.user, e.lab)
        lab_progress_data.append({"lab": e.lab, "progress": p})
        if p["is_complete"]:
            completed_count += 1

    total = enrolled.count()
    return render(
        request,
        "progress_overview.html",
        {
            "active_nav": "progress",
            "user_role_label": role_label,
            "summary": {
                "enrolled_labs": total,
                "completed_labs": completed_count,
                "percent": round((completed_count / total) * 100) if total else 0,
            },
            "lab_progress_data": lab_progress_data,
        },
    )
