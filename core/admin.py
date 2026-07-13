from django.contrib import admin

from .models import (
    Activity,
    ActivityStage,
    Assessment,
    ContainerImage,
    Enrollment,
    FlagSubmission,
    HackPhase,
    InstructorProfile,
    Lab,
    LabEnrollment,
    LabProgress,
    LearningPath,
    Module,
    Progress,
    ResourceProfile,
    PortReservation,
    SandboxSession,
    ScenarioService,
    StudentProfile,
    Tool,
)


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0


class ActivityStageInline(admin.TabularInline):
    model = ActivityStage
    extra = 0


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "order")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "learning_path", "is_published", "order")
    list_filter = ("learning_path", "is_published")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ActivityInline]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "resource_profile", "is_published", "order")
    list_filter = ("module__learning_path", "module", "is_published", "resource_profile")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ActivityStageInline]


@admin.register(ActivityStage)
class ActivityStageAdmin(admin.ModelAdmin):
    list_display = ("activity", "stage_type", "order", "title")
    list_filter = ("stage_type", "activity__module__learning_path")


@admin.register(ResourceProfile)
class ResourceProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "cpu_count", "memory_mb", "time_limit_minutes")


@admin.register(HackPhase)
class HackPhaseAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "command")
    list_filter = ("category",)


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("title", "hack_phase", "instructor", "is_published", "order")
    list_filter = ("hack_phase", "is_published")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(LabEnrollment)
class LabEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "enrolled_at", "is_active")


@admin.register(LabProgress)
class LabProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "stage", "completed_at")


@admin.register(SandboxSession)
class SandboxSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "container_id", "status", "started_at", "expires_at")
    list_filter = ("status",)


@admin.register(ContainerImage)
class ContainerImageAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "image", "container_port")
    list_filter = ("kind",)
    search_fields = ("name", "image")


@admin.register(PortReservation)
class PortReservationAdmin(admin.ModelAdmin):
    list_display = ("port", "session", "created_at")
    readonly_fields = ("port", "session", "created_at")


@admin.register(ScenarioService)
class ScenarioServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "port", "docker_image", "default_flag")


@admin.register(FlagSubmission)
class FlagSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "is_correct", "submitted_at")
    list_filter = ("is_correct",)


admin.site.register(StudentProfile)
admin.site.register(InstructorProfile)
admin.site.register(Enrollment)
admin.site.register(Progress)
admin.site.register(Assessment)
