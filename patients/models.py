from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid

User = get_user_model()


class PatientProfile(models.Model):
    """Patient profile info"""

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("prefere_not_to_say", "Prefer not to say"),
    ]

    BLOOD_TYPE_CHOICES = [
        ("A+", "A Positive"),
        ("A-", "A Negative"),
        ("B+", "B Positive"),
        ("B-", "B Negative"),
        ("O+", "O Positive"),
        ("O-", "O Negative"),
        ("AB+", "AB Positive"),
        ("AB-", "AB Negative"),
        ("unknown", "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient_profile",
        limit_choices_to={"role": "patient"},
    )
    avatar = models.ImageField(upload_to="patients/avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateTimeField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)

    phone_regex = RegexValidator(
        regex=r"^\+?91?\d{9,15}$",
        message="Phone number must use the format: +91-[10 digit number]",
    )

    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True
    )
    emergency_contant_relationship = models.CharField(max_length=50, blank=True)
    blood_type = models.CharField(choices=BLOOD_TYPE_CHOICES, blank=False)
    allergies = models.JSONField(
        default=list, blank=True, help_text="List of allergies"
    )
    cronic_conditions = models.JSONField(
        default=list, blank=True, help_text="List of cronic conditions"
    )
    current_medications = models.JSONField(
        default=list, blank=True, help_text="List of current medications"
    )
    medical_notes = models.TextField(
        blank=True, help_text="Additional medical information"
    )
    share_medical_history = models.BooleanField(default=True)
    allow_emergency_access = models.BooleanField(default=True)
    preferred_language = models.CharField(max_length=10, default="en")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name}"

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar_url
        return None

    @property
    def age(self):
        if dob := self.date_of_birth:
            today = timezone.now().date()
            return today.year - dob.year - (today.month, today.day) < (
                dob.month,
                dob.day,
            )

        return None

    def clean(self):
        if self.user and self.user.role != "patient":
            from django.core.exceptions import ValidationError

            raise ValidationError("User must have a patient role")

    class Meta:
        db_table = "patient_profiles"
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"
        indexes = [models.Index(fields=["user"]), models.Index(fields=["created_at"])]


class PatientMedicalHistory(models.Model):
    """Detailed Medical history"""

    RECORD_TYPE_CHOICES = [
        ("diagnosis", "Diagnosis"),
        ("procedure", "Medical Procedure"),
        ("surgery", "Surgery"),
        ("hospitalization", "Hospitalization"),
        ("vaccication", "Vaccication"),
        ("test_result", "Test Result"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name="medical_history"
    )
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_occured = models.DateField()
    healthcare_provider = models.CharField(max_length=200, blank=True)
    attachments = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.title}"

    class Meta:
        db_table = "patient_medical_history"
        ordering = ["-date_occured", "-created_at"]
