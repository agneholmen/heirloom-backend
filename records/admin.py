from django.contrib import admin
from .models import Record, BirthRecord


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'date_range', 'created_at')
    search_fields = ('title', 'description', 'source')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BirthRecord)
class BirthRecordAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'sex', 'birth_year', 'location', 'father_last_name', 'mother_last_name', 'record')
    search_fields = ('first_name', 'location', 'father_first_name', 'father_last_name', 'mother_first_name', 'mother_last_name')
    list_filter = ('sex', 'birth_year', 'record')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Person Information', {
            'fields': ('record', 'first_name', 'sex', 'birth_date', 'birth_year', 'location')
        }),
        ('Father Information', {
            'fields': ('father_first_name', 'father_last_name', 'father_birth_year', 'father_birth_parish')
        }),
        ('Mother Information', {
            'fields': ('mother_first_name', 'mother_last_name', 'mother_birth_year', 'mother_birth_parish')
        }),
        ('Archive & Notes', {
            'fields': ('archive_info', 'link', 'notes', 'created_at')
        }),
    )

