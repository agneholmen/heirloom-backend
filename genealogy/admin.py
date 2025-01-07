from django.contrib import admin
from .models import (
    Child, 
    Event,
    Family,
    FamilyEvent, 
    Profile, 
    Tree, 
    Individual
)


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
        'birth_place', 'birth_year', 'death_date', 'death_place', 'death_cause', 'death_year'
    ]
    raw_id_fields = ['tree']
    list_filter = ['last_name']

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['id', 'family_id', 'tree', 'husband', 'wife']

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['family', 'indi', 'relation']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_type', 'indi', 'date', 'place', 'description', 'year']

@admin.register(FamilyEvent)
class FamilyEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_type', 'family', 'date', 'place', 'description', 'year']
