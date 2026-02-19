from rest_framework import serializers
from .models import Record, BirthRecord


class RecordSerializer(serializers.ModelSerializer):
    birth_record_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Record
        fields = ['id', 'title', 'description', 'source', 'date_range', 'birth_record_count', 'created_at', 'updated_at']
    
    def get_birth_record_count(self, obj):
        return obj.birth_records.count()


class BirthRecordSerializer(serializers.ModelSerializer):
    record_title = serializers.CharField(source='record.title', read_only=True)
    
    class Meta:
        model = BirthRecord
        fields = [
            'id', 'record', 'record_title',
            'first_name', 'sex', 'birth_date', 'birth_year', 'location',
            'father_first_name', 'father_last_name', 'father_birth_year', 'father_birth_parish',
            'mother_first_name', 'mother_last_name', 'mother_birth_year', 'mother_birth_parish',
            'archive_info', 'link', 'notes', 'created_at'
        ]
