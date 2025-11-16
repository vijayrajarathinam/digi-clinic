from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email field is empty")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password=password, **extra_fields)

    def get_patient(self):
        return self.filter(role="patient", is_active=True)

    def get_consultants(self):
        return self.filter(role="consultant", is_active=True)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("patient", "Patient"),
        ("consultant", "Consultant"),
        ("admin", "Admin"),
    ]

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="patient", db_index=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def mark_email_verified(self):
        """Mark user email as verified"""
        self.is_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["is_verified", "email_verified_at"])

    def update_online_status(self, is_online=True):
        """Update user online field"""
        self.is_online = is_online
        self.last_seen = timezone.now()
        self.save(update_fields=["is_online", "last_seen"])

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email"]),
            models.Index(fields=["is_online"]),
        ]


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "email_verification_tokens"
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "is_used"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()
