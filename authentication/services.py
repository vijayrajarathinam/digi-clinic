from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from django.template.loader import render_to_string
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from .models import User, EmailVerificationToken
from consultants.models import ConsultantProfile
import uuid
import logging

logger = logging.getLogger(__name__)


class AuthenticationService:

    @staticmethod
    def register_user(email, password, first_name, last_name, role="patient"):
        try:
            if User.objects.filter(email=email).exists():
                return None, "User with this email already exists"

            user = User.objects.create_user(
                email=email, password=password,\
                first_name=first_name, last_name=last_name,
                role=role,
            ) # fmt: skip

            if role == "consultant":
                ConsultantProfile.objects.create(user=user)

            logger.info(f"User registered successfully: {email} with role {role}")
            return user, None

        except Exception as ex:
            logger.error(f"Registration failed for {email} : {str(ex)}")
            return None, str(ex)

    @staticmethod
    def authenticate_user(email, password):
        if user := authenticate(email=email, password=password):
            if not user.is_active:
                return None, "User accont is deactivated"

            refresh = RefreshToken.for_user(user)
            user.last_seen = timezone.now()
            logger.info(f"User authenticated successfully: {user.email}")
            return {
                "user": user,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }, None
        else:
            logger.warning(f"Authentication failed for : {email}")
            return None, "Invalid Credentials"

    @staticmethod
    def update_user_status(user, is_online=True):
        try:
            user.is_online = is_online
            user.last_seen = timezone.now()
            user.save(update_fields=["is_online", "last_seen"])

            cache_key = f"user_status_{user.id}"
            cache.set(
                cache_key,
                {"is_online": is_online, "last_seen": user.last_seen.isoformat()},
                timeout=3600,
            )
            logger.debug(f"Update user status for {user.email}: Online={is_online}")

        except Exception as ex:
            logger.error(f"Failed to update user status for {user.email} : {str(ex)}")


class EmailVerificationService:

    @staticmethod
    def send_verification_email(user: User):
        try:
            EmailVerificationToken.objects.filter(user=user, is_used=False).update(
                is_used=True
            )

            verification_token = EmailVerificationToken.objects.create(user=user)
            app_name = getattr(settings, "APP_NAME", "Godson Herbal Clinic App")
            subject = f"Verify your email - {app_name}"
            verification_url = f"{getattr(settings, "FRONTEND_URL", 'http://localhost/3000')}/verify-email?token={verification_token.token}"
            html_message = render_to_string(
                "email/email_verification.html",
                {"user": user, "verification_url": verification_url, "app_name":app_name} # fmt: skip
            )

            plain_message = f"""
                Hi {user.first_name},
                Thank you for signing up for {app_name}!
                Please verify your email addressby clicking the link below:
                {verification_url}
                This link will expire in 24 hours.

                If you didn't create an account, please ignore this email.

                Best regards,
                {app_name} Team
            """

            send_mail(
                subject=subject, message=plain_message, html_message=html_message,
                from_email=getattr(settings, 'FROM_EMAIL', 'noreply@domain.com'),
                recipient_list=[user.email], fail_silently=False
            ) # fmt: skip

            logger.info(f"Verification email sent successfully: {user.email}")
            return True

        except Exception as ex:
            logger.error(f"Verification failed for {user.email} : {str(ex)}")
            return False

    @staticmethod
    def verify_email_token(token: str):
        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
            if not verification_token.is_valid():
                return None, (
                    "Verification link has expired"
                    if verification_token.is_expired()
                    else "Verification link has already been used"
                )

            verification_token.is_used = True
            verification_token.save()

            user = verification_token.user
            user.mark_email_verified()

            logger.info(f"Email verfied successfully for user: {user.email}")
            return user, None
        except EmailVerificationToken.DoesNotExist:
            logger.warning(f"Invalid verification token {token} for {user.email}")
            return None, "Invalid verification token"
        except Exception as ex:
            logger.error(f"Email verification failed for token {token}: {str(ex)}")
            return None, f"verification failed: {str(ex)}"

    @staticmethod
    def resend_verification_email(user: User):
        if user.is_verified:
            return False, "Email is already verified"

        recent_token = EmailVerificationToken.objects.filter(
            user=user, created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()

        if recent_token >= 3:
            message = """Too many verification emails sent. \
                Please wait before requesting other"""

            return False, message

        if success := EmailVerificationService.send_verification_email(user):
            return success, "Verification sent successfully to email"

        return False, "Failed to send verification email"
