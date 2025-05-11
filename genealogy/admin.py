from django.contrib import admin
from .models import (
    Archive,
    Child, 
    Event,
    Family,
    FamilyEvent,
    Image,
    ImagePerson,
    Person,
    Source, 
    Tree
)

@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'upload_date', 'name', 'gedcom_file']
    raw_id_fields = ['user']

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'indi_id', 'tree', 'first_name', 'last_name', 'sex', 'death_cause'
    ]
    raw_id_fields = ['tree']
    list_filter = ['last_name']

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ['id', 'family_id', 'tree', 'husband', 'wife']

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['family', 'person', 'relation']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_type', 'person', 'date', 'place', 'description', 'year']

@admin.register(FamilyEvent)
class FamilyEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_type', 'family', 'date', 'place', 'description', 'year']

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ['title', 'tree']

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'archive', 'web_link']

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['user', 'tree', 'title', 'created', 'slug', 'image']

@admin.register(ImagePerson)
class ImagePersonAdmin(admin.ModelAdmin):
    list_display = ['person', 'image']