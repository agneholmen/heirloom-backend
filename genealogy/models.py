from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from datetime import date


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
    

class Tree(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    upload_date = models.DateField(default=date.today)
    name = models.CharField(
        blank=True,
        null=True,
        max_length=100
    )
    gedcom_file = models.FileField(
        upload_to='users/%Y/%m/%d',
        blank=True
    )


class Individual(models.Model):
    SEX_CHOICES = (
        ("M", "Man"),
        ("F", "Kvinna"),
        ("U", "Unknown"),
    )

    indi_id = models.CharField(max_length=20, null=True, blank=True)
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, default="U")
    birth_date = models.CharField(max_length=100, null=True, blank=True)
    birth_place = models.CharField(max_length=100, null=True, blank=True)
    death_date = models.CharField(max_length=100, null=True, blank=True)
    death_place = models.CharField(max_length=100, null=True, blank=True)
    death_cause = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tree', 'indi_id'], name='Tree and INDI combination')
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

# Removes the GEDCOM file when you remove a Tree instance
@receiver(post_delete, sender=Tree)
def tree_post_delete_handler(sender, **kwargs):
    tree = kwargs['instance']
    storage, path = tree.gedcom_file.storage, tree.gedcom_file.path
    storage.delete(path)