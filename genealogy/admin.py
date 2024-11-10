from django.contrib import admin
from .models import Profile, Tree, Individual


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo', 'description']
    raw_id_fields = ['user']

@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'upload_date', 'name', 'gedcom_file']
    raw_id_fields = ['user']

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'indi_id', 'tree', 'first_name', 'last_name', 'sex', 'birth_date',
        'birth_place', 'death_date', 'death_place', 'death_cause'
    ]
    raw_id_fields = ['tree']