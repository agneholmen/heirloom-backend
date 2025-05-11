from django.contrib import admin
from .models import Action, Follow, User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'sex', 'email']
    ordering = ['username']

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['user_from', 'user_to', 'created']

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'target', 'created']
    list_filter = ['created']