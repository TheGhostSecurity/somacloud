from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Activity, ActivityStage, Enrollment, LearningPath, Module, Progress, ResourceProfile


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adminuser",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )
        Group.objects.get_or_create(name="Instructor")

    def test_admin_can_create_instructor_user(self):
        self.client.login(username="adminuser", password="StrongPass123!")
        response = self.client.post(
            reverse("create_user"),
            {
                "username": "trainer1",
                "first_name": "Train",
                "last_name": "Er",
                "email": "trainer@example.com",
                "role": "instructor",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )

        self.assertRedirects(response, reverse("control_panel"))
        created_user = User.objects.get(username="trainer1")
        self.assertTrue(created_user.groups.filter(name="Instructor").exists())
        self.assertFalse(created_user.is_staff)

    def test_dashboard_redirects_admin_to_control_panel(self):
        self.client.login(username="adminuser", password="StrongPass123!")
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("control_panel"))

    def test_non_admin_cannot_access_control_panel(self):
        user = User.objects.create_user(username="student1", password="StrongPass123!")
        self.client.login(username=user.username, password="StrongPass123!")
        response = self.client.get(reverse("control_panel"))
        self.assertEqual(response.status_code, 302)

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login")
        self.assertContains(response, "Sign Up")

    def test_signup_creates_student_account(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newstudent",
                "first_name": "New",
                "last_name": "Student",
                "email": "student@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        created_user = User.objects.get(username="newstudent")
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.groups.filter(name="Instructor").exists())

    def test_admin_url_shows_custom_control_panel(self):
        self.client.login(username="adminuser", password="StrongPass123!")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform Overview")

    def test_control_panel_name_uses_admin_url(self):
        self.assertEqual(reverse("control_panel"), "/admin/")

    def test_home_page_stays_visible_for_authenticated_users(self):
        self.client.login(username="adminuser", password="StrongPass123!")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")


class LearningEngineTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="student1", password="StrongPass123!")
        self.resource = ResourceProfile.objects.create(name="Light", cpu_count=1, memory_mb=256, time_limit_minutes=5)
        self.path = LearningPath.objects.create(title="Foundations", slug="foundations", order=1)
        self.module = Module.objects.create(learning_path=self.path, title="Module One", slug="module-one", order=1)
        self.activity = Activity.objects.create(
            module=self.module,
            resource_profile=self.resource,
            title="First Activity",
            slug="first-activity",
            order=1,
        )
        self.stage = ActivityStage.objects.create(
            activity=self.activity,
            stage_type=ActivityStage.THEORY,
            title="Theory",
            content="Read this first.",
            order=1,
        )
        Enrollment.objects.create(user=self.student, learning_path=self.path)

    def test_learning_path_page_lists_database_records(self):
        self.client.login(username="student1", password="StrongPass123!")
        response = self.client.get(reverse("learning_paths"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Foundations")

    def test_generic_activity_page_loads_activity_stages_from_database(self):
        self.client.login(username="student1", password="StrongPass123!")
        response = self.client.get(
            reverse(
                "activity_detail",
                kwargs={
                    "path_slug": self.path.slug,
                    "module_slug": self.module.slug,
                    "activity_slug": self.activity.slug,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First Activity")
        self.assertContains(response, "Read this first.")

    def test_completing_stage_creates_progress_record(self):
        self.client.login(username="student1", password="StrongPass123!")
        response = self.client.post(reverse("complete_activity_stage", kwargs={"stage_id": self.stage.id}))
        self.assertRedirects(
            response,
            reverse(
                "activity_detail",
                kwargs={
                    "path_slug": self.path.slug,
                    "module_slug": self.module.slug,
                    "activity_slug": self.activity.slug,
                },
            ),
        )
        self.assertTrue(
            Progress.objects.filter(user=self.student, activity_stage=self.stage, completed_at__isnull=False).exists()
        )


class ContentSyncTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="contentstudent", password="StrongPass123!")

    def test_sync_content_imports_file_backed_activity_without_sandbox(self):
        call_command("sync_content", verbosity=0)
        activity = Activity.objects.get(slug="first-activity")
        self.assertEqual(activity.title, "First Activity")
        self.assertTrue(activity.stages.filter(stage_type=ActivityStage.THEORY, content_file__endswith="theory.md").exists())
        self.assertFalse(activity.stages.filter(stage_type=ActivityStage.SANDBOX).exists())

    def test_activity_detail_renders_imported_markdown_content(self):
        call_command("sync_content", verbosity=0)
        path = LearningPath.objects.get(slug="foundations")
        module = Module.objects.get(learning_path=path, slug="module-one")
        activity = Activity.objects.get(module=module, slug="first-activity")
        Enrollment.objects.create(user=self.student, learning_path=path)

        self.client.login(username="contentstudent", password="StrongPass123!")
        response = self.client.get(
            reverse(
                "activity_detail",
                kwargs={
                    "path_slug": path.slug,
                    "module_slug": module.slug,
                    "activity_slug": activity.slug,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduce the concept")
        self.assertNotContains(response, "Sandbox")
