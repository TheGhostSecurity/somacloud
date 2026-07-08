from django.conf import settings
from django.db import models
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    profile_image = models.ImageField(upload_to="student-profiles/", blank=True, null=True)

    def __str__(self):
        return f"StudentProfile({self.user.username})"


class InstructorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor_profile")
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"InstructorProfile({self.user.username})"


class ResourceProfile(models.Model):
    name = models.CharField(max_length=80, unique=True)
    cpu_count = models.PositiveSmallIntegerField(default=1)
    memory_mb = models.PositiveIntegerField(default=256)
    time_limit_minutes = models.PositiveIntegerField(default=5)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["cpu_count", "memory_mb", "time_limit_minutes", "name"]

    def __str__(self):
        return self.name


class HackPhase(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Tool(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    command = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=80, blank=True)
    logo_url = models.URLField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class ScenarioService(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    docker_image = models.CharField(max_length=200, blank=True, default="")
    port = models.PositiveIntegerField(default=80)
    script_module = models.CharField(max_length=200, blank=True, help_text="Python module path, e.g. scenario_services.sql_injection")
    default_flag = models.CharField(max_length=500, blank=True, default="", help_text="The flag defined in the script, auto-populated when instructor selects this service.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Lab(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    hack_phase = models.ForeignKey(HackPhase, on_delete=models.CASCADE, related_name="labs")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_labs")
    summary = models.TextField(blank=True)
    theory_content = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Student walkthrough. Use {{SERVICE_IP}} for the service container IP.")
    tools = models.ManyToManyField(Tool, related_name="labs", blank=True)
    resource_profile = models.ForeignKey(ResourceProfile, on_delete=models.PROTECT, related_name="labs")
    scenario_service = models.ForeignKey(ScenarioService, on_delete=models.SET_NULL, null=True, blank=True, related_name="labs")
    sandbox_image = models.CharField(max_length=200, blank=True, default="")
    sandbox_config = models.TextField(blank=True)
    flag = models.CharField(max_length=500, blank=True, help_text="The flag students must find and submit to complete the lab.")
    flag_hint = models.TextField(blank=True, help_text="Hint shown when a student submits a wrong flag.")
    challenge_type = models.CharField(max_length=16, choices=[("flag", "Flag"), ("question", "Question")], default="flag", help_text="Flag requires finding a hidden value. Question requires answering a quiz.")
    challenge_question = models.TextField(blank=True, help_text="The question shown to students when challenge_type is Question.")
    challenge_options = models.TextField(blank=True, help_text='JSON array of answer options, e.g. ["Option A","Option B","Option C","Option D"]')
    challenge_answer = models.CharField(max_length=500, blank=True, help_text="Correct answer (text for text answer, or full option text for multiple choice).")

    def get_options_list(self):
        """Parse challenge_options JSON into a Python list."""
        import json
        if not self.challenge_options:
            return []
        try:
            return json.loads(self.challenge_options)
        except (json.JSONDecodeError, TypeError):
            return []
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hack_phase__order", "order", "title"]
        constraints = [
            models.UniqueConstraint(fields=["hack_phase", "slug"], name="unique_lab_slug_per_phase"),
        ]

    def __str__(self):
        return self.title


class LabEnrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_enrollments")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "lab"], name="unique_enrollment_per_user_lab"),
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in lab {self.lab.title}"


class LabProgress(models.Model):
    THEORY = "theory"
    SANDBOX = "sandbox"
    CHALLENGE = "challenge"
    COMPLETE = "complete"

    STAGE_CHOICES = (
        (THEORY, "Theory"),
        (SANDBOX, "Sandbox"),
        (CHALLENGE, "Challenge"),
        (COMPLETE, "Complete"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_progress_entries")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="progress_entries")
    stage = models.CharField(max_length=32, choices=STAGE_CHOICES)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lab__order", "stage"]
        constraints = [
            models.UniqueConstraint(fields=["user", "lab", "stage"], name="unique_progress_per_user_lab_stage"),
        ]

    @property
    def is_complete(self):
        return self.completed_at is not None

    def mark_complete(self):
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.save(update_fields=["completed_at", "updated_at"])

    def __str__(self):
        return f"{self.user.username}: {self.lab} - {self.get_stage_display()}"


class SandboxSession(models.Model):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    EXPIRED = "expired"
    ERROR = "error"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (RUNNING, "Running"),
        (STOPPED, "Stopped"),
        (EXPIRED, "Expired"),
        (ERROR, "Error"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sandbox_sessions")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="sandbox_sessions")
    container_id = models.CharField(max_length=128, blank=True)
    service_container_id = models.CharField(max_length=128, blank=True)
    service_ip = models.CharField(max_length=45, blank=True, help_text="IP of the scenario service container")
    service_port = models.IntegerField(null=True, blank=True, help_text="External port mapped for the service container")
    server_url = models.CharField(max_length=500, blank=True)
    terminal_url = models.CharField(max_length=500, blank=True)
    terminal_port = models.IntegerField(null=True, blank=True, help_text="Port of per-sandbox ttyd instance")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PENDING)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    stopped_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} sandbox for {self.lab.title} ({self.get_status_display()})"


class FlagSubmission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="flag_submissions")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="flag_submissions")
    submitted_flag = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.username} submitted flag for {self.lab.title} ({'correct' if self.is_correct else 'wrong'})"


class LearningPath(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


class Module(models.Model):
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["learning_path__order", "order", "title"]
        constraints = [
            models.UniqueConstraint(fields=["learning_path", "slug"], name="unique_module_slug_per_path"),
        ]

    def __str__(self):
        return self.title


class Activity(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="activities")
    resource_profile = models.ForeignKey(ResourceProfile, on_delete=models.PROTECT, related_name="activities")
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    summary = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["module__learning_path__order", "module__order", "order", "title"]
        constraints = [
            models.UniqueConstraint(fields=["module", "slug"], name="unique_activity_slug_per_module"),
        ]

    def __str__(self):
        return self.title


class ActivityStage(models.Model):
    THEORY = "theory"
    GUIDED_PRACTICE = "guided_practice"
    SANDBOX = "sandbox"
    CHALLENGE = "challenge"
    REFLECTION = "reflection"
    ASSESSMENT = "assessment"

    STAGE_CHOICES = (
        (THEORY, "Theory"),
        (GUIDED_PRACTICE, "Guided Practice"),
        (SANDBOX, "Sandbox"),
        (CHALLENGE, "Challenge"),
        (REFLECTION, "Reflection"),
        (ASSESSMENT, "Assessment"),
    )

    DEFAULT_STAGE_ORDER = {
        THEORY: 1,
        GUIDED_PRACTICE: 2,
        SANDBOX: 3,
        CHALLENGE: 4,
        REFLECTION: 5,
        ASSESSMENT: 6,
    }

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="stages")
    stage_type = models.CharField(max_length=32, choices=STAGE_CHOICES)
    title = models.CharField(max_length=160)
    content = models.TextField(blank=True)
    content_file = models.CharField(max_length=500, blank=True)
    config_file = models.CharField(max_length=500, blank=True)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["activity__module__learning_path__order", "activity__module__order", "activity__order", "order"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "stage_type"], name="unique_stage_type_per_activity"),
            models.UniqueConstraint(fields=["activity", "order"], name="unique_stage_order_per_activity"),
        ]

    def save(self, *args, **kwargs):
        if self.stage_type and not self.order:
            self.order = self.DEFAULT_STAGE_ORDER.get(self.stage_type, 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity}: {self.get_stage_type_display()}"


class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "learning_path"], name="unique_enrollment_per_user_path"),
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in {self.learning_path.title}"


class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_entries")
    activity_stage = models.ForeignKey(ActivityStage, on_delete=models.CASCADE, related_name="progress_entries")
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["activity_stage__activity__order", "activity_stage__order"]
        constraints = [
            models.UniqueConstraint(fields=["user", "activity_stage"], name="unique_progress_per_user_stage"),
        ]

    @property
    def is_complete(self):
        return self.completed_at is not None

    def mark_complete(self):
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.save(update_fields=["completed_at", "updated_at"])

    def __str__(self):
        return f"{self.user.username}: {self.activity_stage}"


class Assessment(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE, related_name="assessment")
    instructions = models.TextField(blank=True)
    passing_score = models.PositiveSmallIntegerField(default=70)

    def __str__(self):
        return f"Assessment for {self.activity.title}"

