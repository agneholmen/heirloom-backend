from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from datetime import date


def users_file_location(instance, filename):
    date_string = date.today().strftime("%Y/%m/%d")
    return f"users/{instance.user.username}/{date_string}/{filename}"


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
        upload_to=users_file_location,
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
        upload_to=users_file_location,
        blank=True,
        null=True
    )

    def __str__(self) -> str:
        return self.name


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
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    death_date = models.CharField(max_length=100, null=True, blank=True)
    death_place = models.CharField(max_length=100, null=True, blank=True)
    death_cause = models.CharField(max_length=100, null=True, blank=True)
    death_year = models.PositiveSmallIntegerField(null=True, blank=True)
    alive = models.BooleanField(default=False)
    added = models.DateField(auto_now_add=True)
    last_updated = models.DateField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tree', 'indi_id'], name='Tree and INDI combination')
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

class Family(models.Model):
    family_id = models.CharField(max_length=20)
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE)
    husband = models.ForeignKey(
        Individual,
        on_delete=models.SET_NULL,
        related_name="families_as_husband",
        null=True,
        blank=True
    )
    wife = models.ForeignKey(
        Individual,
        on_delete=models.SET_NULL,
        related_name="families_as_wife",
        null=True,
        blank=True
    )
    marriage_date = models.CharField(max_length=100, null=True, blank=True)
    marriage_place = models.CharField(max_length=100, null=True, blank=True)

    def clean(self):
        if self.husband and self.husband.tree != self.tree:
            raise ValidationError("Husband must belong to the same tree as the family.")
        if self.wife and self.wife.tree != self.tree:
            raise ValidationError("Wife must be long to the same tree as the family.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tree', 'family_id'], name='Tree and family combination')
        ]
        verbose_name_plural = "Families"

class Child(models.Model):
    class Relation(models.TextChoices):
        ADOPTED = "A", _("Adopted")
        BIOLOGICAL = "B", ("Biological")
        FOSTER = 'F', _("Foster")
        UNKNOWN = 'U', _("Unknown")

    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        null=True,
        blank=True                       
    )
    indi = models.ForeignKey(
        Individual,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    relation = models.CharField(
        choices=Relation,
        max_length=1,
        default=Relation.BIOLOGICAL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['family', 'indi'], name='Individual and family combination')
        ]
        verbose_name_plural = "Children"

# Removes the GEDCOM file when you remove a Tree instance
@receiver(post_delete, sender=Tree)
def tree_post_delete_handler(sender, **kwargs):
    tree = kwargs['instance']
    storage, path = tree.gedcom_file.storage, tree.gedcom_file.path
    storage.delete(path)