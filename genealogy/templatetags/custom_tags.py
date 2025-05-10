from django import template

register = template.Library()

@register.simple_tag
def follow_status(this_user, user):
    if user in this_user.following.all():
        return 'Unfollow'
    else:
        return 'Follow'