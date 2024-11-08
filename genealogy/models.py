from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", _("Male")
        FEMALE = 'F', _("Female")
        UNKNOWN = 'U', _("Unknown")


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='users/%Y/%m/%d',
        blank=True
    )
    description = models.TextField(blank=True, null=True)
    sex = models.CharField(
        max_length=1,
        choices=Sex,
        default=Sex.UNKNOWN
    )

    def __str__(self) -> str:
        return f'Profile of {self.user.username}'