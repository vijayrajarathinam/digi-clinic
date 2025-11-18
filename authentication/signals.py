from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            if instance.role == "patient":
                from patients.models import PatientProfile

                PatientProfile.objects.create(user=instance)
                logger.info(f"Created patient profile for user {instance.id}")
            elif instance.role == "consultant":
                from consultants.models import ConsultantProfile

                ConsultantProfile.objects.create(user=instance)
                logger.info(f"Created Consultant profile for user {instance.id}")
        except Exception as ex:
            logger.error(f"Error while creating user profile {instance.id}: {str(ex)}")
