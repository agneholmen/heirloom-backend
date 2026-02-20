from datetime import date
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from easy_thumbnails.files import get_thumbnailer

def users_file_location(instance, filename):
    date_string = date.today().strftime("%Y/%m/%d")
    return f"users/{instance.username}/{date_string}/{filename}"

class User(AbstractUser):
    SEX_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("U", "Unknown"),
    )

    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to=users_file_location,
        blank=True
    )
    description = models.TextField(blank=True)
    sex = models.CharField(
        max_length=1,
        choices=SEX_CHOICES,
        default="U"
    )

    following = models.ManyToManyField(
        'self',
        through='Follow',
        related_name='followers',
        symmetrical=False,
    )

    def follow(self, user):
        if user not in self.following.all():
            Follow.objects.create(user_from=self, user_to=user)

    def unfollow(self, user):
        if user in self.following.all():
            Follow.objects.filter(user_from=self, user_to=user).delete()

class Follow(models.Model):
    user_from = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='rel_from_set',
        on_delete=models.CASCADE
    )

    user_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='rel_to_set',
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created']),
        ]
        ordering = ['-created']

    def __str__(self):
        return f"{self.user_from} follows {self.user_to}"

class Action(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='actions',
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    target_ct = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name='target_obj',
        on_delete=models.CASCADE
    )
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('target_ct', 'target_id')

    class Meta:
        indexes = [
            models.Index(fields=['-created']),
            models.Index(fields=['target_ct', 'target_id']),
        ]
        ordering = ['-created']


# Removes the photo file when you remove a User account
@receiver(post_delete, sender=User)
def user_post_delete_handler(sender, **kwargs):
    user = kwargs['instance']
    if not hasattr(user, 'photo') or not user.photo:
        return

    try:
        storage, path = user.photo.storage, user.photo.path
        storage.delete(path)
    except (ValueError, OSError):
        return

    thumbnailer = get_thumbnailer(user.photo)
    thumbnailer.delete_thumbnails()