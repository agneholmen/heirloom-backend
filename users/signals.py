from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from .models import Follow, Action, User
from genealogy.models import Image, Image_Like, Image_Comment

# Track follow/unfollow
@receiver(post_save, sender=Follow)
def create_follow_action(sender, instance, created, **kwargs):
    if created:
        Action.objects.create(
            user=instance.user_from,
            target=instance
        )

@receiver(post_delete, sender=Follow)
def delete_follow_action(sender, instance, **kwargs):
    Action.objects.filter(
        user=instance.user_from,
        target_ct=ContentType.objects.get_for_model(Follow),
        target_id=instance.id
    ).delete()

# Track like/unlike images
@receiver(post_save, sender=Image_Like)
def create_image_like_action(sender, instance, created, **kwargs):
    if created:
        Action.objects.create(
            user=instance.user,
            target=instance
        )

@receiver(post_delete, sender=Image_Like)
def delete_image_like_action(sender, instance, **kwargs):
    Action.objects.filter(
        user=instance.user,
        target_ct=ContentType.objects.get_for_model(Image_Like),
        target_id=instance.id
    ).delete()

# Track commenting on images
@receiver(post_save, sender=Image_Comment)
def create_image_comment_action(sender, instance, created, **kwargs):
    if created:
        Action.objects.create(
            user=instance.user,
            target=instance
        )

@receiver(post_delete, sender=Image_Comment)
def delete_image_comment_action(sender, instance, **kwargs):
    Action.objects.filter(
        user=instance.user,
        target_ct=ContentType.objects.get_for_model(Image_Comment),
        target_id=instance.id
    ).delete()