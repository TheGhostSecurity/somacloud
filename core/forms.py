import json

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import ContainerImage, HackPhase, Lab, ResourceProfile, StudentProfile


User = get_user_model()


ROLE_CHOICES = (
    ("user", "Student"),
    ("instructor", "Instructor"),
    ("admin", "Administrator"),
)

ADMIN_MANAGED_ROLE_CHOICES = (
    ("user", "Student"),
    ("instructor", "Instructor"),
)


class UserManagementForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ADMIN_MANAGED_ROLE_CHOICES)
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role", "password1", "password2")

    def __init__(self, *args, allow_admin_role=False, **kwargs):
        super().__init__(*args, **kwargs)
        if allow_admin_role:
            self.fields["role"].choices = ROLE_CHOICES
        for field_name, field in self.fields.items():
            css_class = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            field.widget.attrs["class"] = css_class
            if field_name in {"password1", "password2"}:
                field.widget.attrs["placeholder"] = "Enter a secure password"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")

        if password1:
            try:
                validate_password(password1)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data["role"]
        user.is_staff = role == "admin"
        user.is_superuser = role == "admin"
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
            assign_role(user, role)

        return user


def assign_role(user, role):
    user.groups.clear()
    if role == "instructor":
        instructor_group, _ = Group.objects.get_or_create(name="Instructor")
        user.groups.add(instructor_group)


class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            if field_name in {"password1", "password2"}:
                field.widget.attrs["placeholder"] = "Create a password"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")

        if password1:
            try:
                validate_password(password1)
            except ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            assign_role(user, "user")
        return user


class StudentProfileImageForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("profile_image",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profile_image"].widget.attrs.update(
            {
                "class": "block w-full text-sm text-slate-600 file:mr-4 file:rounded-full file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-blue-500",
                "accept": "image/*",
            }
        )


class LabForm(forms.ModelForm):
    class Meta:
        model = Lab
        fields = [
            "title",
            "hack_phase",
            "summary",
            "terminal_container",
            "service_containers",
            "notes",
            "theory_content",
            "resource_profile",
            "challenge_type",
            "challenge_question",
            "challenge_options",
            "challenge_answer",
            "flag",
            "flag_hint",
        ]
        widgets = {
            "flag": forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 font-mono"}),
            "challenge_options": forms.Textarea(attrs={"rows": 3, "placeholder": '["Option A","Option B","Option C","Option D"]'}),
        }
        help_texts = {
            "theory_content": "Supports Markdown: # headers, - lists, ``` code blocks, **bold**, *italic*.",
            "notes": "Supports Markdown. Use {{SERVICE_IP}} for the first target, or {{SERVICE_ENDPOINTS}} for all targets.",
            "flag": "The secret flag students must find and submit. For Question challenge type, leave blank.",
            "flag_hint": "Shown when a student submits an incorrect flag.",
            "challenge_type": "Flag = hidden value in service. Question = quiz when no service is used.",
            "challenge_question": "The question students must answer. Used when challenge_type is Question.",
            "challenge_options": 'JSON array of options. Leave empty for text answer. Example: ["Option A","Option B","Option C","Option D"]',
            "challenge_answer": "The correct answer. For multiple choice, enter the exact option text.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_css = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        area_css = base_css + " font-mono"

        self.fields["terminal_container"] = forms.CharField(
            label="Terminal Container Image",
            help_text="Docker image tag for the browser terminal, e.g. ghostriley23/kali-ttyd:latest",
            required=True,
            widget=forms.TextInput(attrs={"class": base_css, "placeholder": "e.g. ghostriley23/kali-ttyd:latest"}),
        )
        self.fields["service_containers"] = forms.CharField(
            label="Service Container Images",
            help_text="Docker image tags for vulnerable services, one per line or comma-separated.",
            required=False,
            widget=forms.Textarea(attrs={"class": base_css + " h-32 font-mono", "placeholder": "e.g. ghostriley23/vuln-webapp:latest"}),
        )

        if self.instance and self.instance.pk:
            if self.instance.terminal_container_id:
                self.fields["terminal_container"].initial = self.instance.terminal_container.image
            services_qs = self.instance.service_containers.all()
            if services_qs:
                self.fields["service_containers"].initial = "\n".join(s.image for s in services_qs)

        hints = {
            "hack_phase": "Run `python manage.py seed_data` if this is empty.",
            "resource_profile": "Run `python manage.py seed_data` if this is empty.",
        }
        for field_name, field in self.fields.items():
            if field_name in ("terminal_container", "service_containers"):
                continue
            if field_name in ("theory_content", "notes"):
                field.widget.attrs["class"] = area_css + " h-24"
                field.widget.attrs["placeholder"] = "Write in Markdown (# headers, - lists, ``` code)..."
            elif field_name == "challenge_question":
                field.widget.attrs["class"] = area_css + " h-32"
                field.widget.attrs["placeholder"] = "Enter the question students must answer..."
            elif field_name == "flag_hint":
                field.widget.attrs["class"] = area_css + " h-24"
            elif field_name == "summary":
                field.widget.attrs["class"] = base_css + " h-24"
            else:
                if "class" not in field.widget.attrs:
                    field.widget.attrs["class"] = base_css
            if field_name in hints:
                field.help_text = hints[field_name]

    def clean_challenge_options(self):
        val = self.cleaned_data.get("challenge_options", "")
        if not val:
            return val
        try:
            parsed = json.loads(val)
            if not isinstance(parsed, list):
                raise forms.ValidationError("Must be a JSON array, e.g. [\"A\",\"B\"]")
            return val
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON. Use format: [\"Option A\",\"Option B\",\"Option C\"]")

    def clean_terminal_container(self):
        value = self.cleaned_data.get("terminal_container", "").strip()
        if not value:
            raise forms.ValidationError("A terminal container image is required.")
        if "/" not in value:
            raise forms.ValidationError("Must be a full Docker image tag (e.g. ghostriley23/kali-ttyd:latest)")
        name = value.split("/")[-1].split(":")[0].replace("_", "-").replace(".", "-")
        container, _ = ContainerImage.objects.get_or_create(
            image=value,
            defaults={
                "name": name,
                "kind": ContainerImage.TERMINAL,
                "container_port": 7681,
                "description": "Auto-created from lab form.",
            },
        )
        return container

    def clean_service_containers(self):
        value = self.cleaned_data.get("service_containers", "").strip()
        if not value:
            return []
        tags = [t.strip() for t in value.replace(",", "\n").split("\n") if t.strip()]
        containers = []
        for tag in tags:
            if "/" not in tag:
                raise forms.ValidationError(f"'{tag}' is not a valid Docker image tag (e.g. namespace/repo:tag)")
            name = tag.split("/")[-1].split(":")[0].replace("_", "-").replace(".", "-")
            container, _ = ContainerImage.objects.get_or_create(
                image=tag,
                defaults={
                    "name": name,
                    "kind": ContainerImage.SERVICE,
                    "container_port": 80,
                    "description": "Auto-created from lab form.",
                },
            )
            containers.append(container)
        return containers

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("terminal_container"):
            self.add_error("terminal_container", "A terminal container image is required.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.title)[:180]
            slug = base_slug
            n = 1
            while Lab.objects.filter(hack_phase=instance.hack_phase, slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            instance.slug = slug
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ResourceProfileForm(forms.ModelForm):
    class Meta:
        model = ResourceProfile
        fields = ["name", "cpu_count", "memory_mb", "time_limit_minutes", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "cpu_count": "Number of CPU cores allocated to the sandbox container.",
            "memory_mb": "Memory limit in megabytes.",
            "time_limit_minutes": "Maximum session duration in minutes.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_css = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        for field_name, field in self.fields.items():
            if field_name == "description":
                field.widget.attrs["class"] = base_css + " h-24"
            elif field_name in ("cpu_count", "memory_mb", "time_limit_minutes"):
                field.widget.attrs["class"] = base_css + " w-32"
            else:
                field.widget.attrs["class"] = base_css


class LabQuickForm(forms.ModelForm):
    class Meta:
        model = Lab
        fields = ["title", "hack_phase", "summary", "resource_profile"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_css = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        for field in self.fields.values():
            field.widget.attrs["class"] = base_css


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_css = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        for field in self.fields.values():
            field.widget.attrs["class"] = base_css


def get_role_label(user):
    if user.is_staff or user.is_superuser:
        return "Administrator"
    if user.groups.filter(name__iexact="Instructor").exists():
        return "Instructor"
    return "Student"
