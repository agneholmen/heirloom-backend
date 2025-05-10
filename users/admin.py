from django.contrib import admin
from .models import Follow, User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'sex', 'email']
    ordering = ['username']

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['user_from', 'user_to', 'created']