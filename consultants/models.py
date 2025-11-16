from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from calendar import day_name
import uuid

User = get_user_model()


class Speciality(models.Model):
    """Medical Speciality"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "specialties"
        verbose_plural_name = "Specialties"
        ordering = ["name"]


class ConsultantProfile(models.Model):
    """Consultant profile info"""

    CONSULTATION_TYPE_CHOICES = [
        ("video", "Video Consultation"),
        ("audio", "Audio Only"),
        ("chat", "Text Chat"),
        ("all", "All Types"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="consultant_profile",
        limit_choices_to={"role": "consultant"},
    )
    speciality = models.ForeignKey(
        Speciality, on_delete=models.PROTECT, related_name="consultant_speciality"
    )
    avatar = models.ImageField(upload_to="consultants/avatar/", blank=True, null=True)
    bio = models.TextField(max_length=1000, blank=True)
    years_of_experience = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(50)]
    )
    license_number = models.CharField(max_length=100, unique=True)
    medical_degree = models.CharField(max_length=200, blank=True)
    board_certifications = models.JSONField(default=list, blank=True)
    additional_qualification = models.JSONField(default=list, blank=True)

    phone_regex = RegexValidator(
        regex=r"^\+?91?\d{9,15}$",
        message="Phone number must use the format: +91-[10 digit number]",
    )

    phone_number = models.CharField(
        validators=[phone_regex], max_length=17, blank=False
    )
    clinic_name = models.CharField(max_length=200, blank=True)
    clinic_address = models.TextField(max_length=300, blank=True)
    clinic_city = models.CharField(max_length=100, blank=True)
    clinic_country = models.CharField(max_length=100, blank=True)
    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    consultation_duration = models.PositiveIntegerField(
        default=50,
        help_text="Default consultation duration in minutes",
        validators=[MaxValueValidator(50)],
    )
    consultation_types = models.CharField(
        max_length=10, choices=CONSULTATION_TYPE_CHOICES, default="all"
    )
    language_spoken = models.JSONField(default=list, blank=True)
    is_available = models.BooleanField(default=True)
    availablity_schedule = models.JSONField(
        default=dict, blank=True, help_text="Weekly schedule with time slots"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    total_consultations = models.PositiveIntegerField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.full_name} - {self.speciality.name}"

    @property
    def avatar_url(self):
        if avatar := self.avatar:
            return avatar.url
        return None

    def verify_consultant(self):
        """Mark consultant as verified"""
        self.is_verified = True
        self.verification_date = timezone.now().date()
        self.save(update_fields=["is_verified", "verification_date"])

    def update_rating(self):
        """update rating"""
        from django.db.models import Avg

        if avg_rating := self.reviews.aggregate(Avg("rating"))["rating_avg"]:
            self.rating = round(avg_rating, 2)
            self.save(update_fields=["rating"])

    def clean(self):
        if self.user and self.user.role != "consultant":
            from django.core.exceptions import ValidationError

            raise ValidationError("User must have a consultant role")

    class Meta:
        db_table = "consultant_profile"
        verbose_name = "Consultant Profile"
        verbose_name_plural = "Consultant Profiles"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["speciality"]),
            models.Index(fields=["is_verified", "is_available"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["rating"]),
        ]


class ConsultantReview(models.Model):
    """Reviews and Ratings"""

    RATING_CHOICES = [(i, f"{i} Star{'s' if i < 1 else ''}") for i in range(1, 6)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultant = models.ForeignKey(
        ConsultantProfile, on_delete=models.CASCADE, related_name="reviews"
    )
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role": "patients"}
    )
    rating = models.IntegerField(choices=RATING_CHOICES)
    review_text = models.TextField(max_length=100, blank=True)
    is_verified_consultation = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        patient_name = "Anonymous" if self.is_anonymous else self.patient.full_name
        return f"{patient_name} -> Dr. {self.consultant.full_name} ({self.rating} *)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.consultant.update_rating()

    class Meta:
        db_table = "consultant_review"
        unique_together = ["consultant", "patient"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["consultant", "rating"]),
            models.Index(fields=["created_at"]),
        ]


class ConsultantAvailability(models.Model):
    """available time of consultant"""

    DAY_CHOICES = list((i, day) for i, day in enumerate(day_name))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultant = models.ForeignKey(
        ConsultantProfile, on_delete=models.CASCADE, related_name="available_slots"
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.consultant.user.full_name} - {self.get_day_of_the_week_display} {self.start_time} - {self.end_time}"

    @property
    def get_day_of_the_week_display(self):
        return self.DAY_CHOICES[self.day_of_week]

    class Meta:
        db_table = "consultant_availability"
        unique_together = ["consultant", "day_of_week", "start_time"]
        ordering = ["day_of_week", "start_time"]
