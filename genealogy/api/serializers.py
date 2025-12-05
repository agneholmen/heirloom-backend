from rest_framework import serializers
from genealogy.models import Person, Tree

class TreeSerializer(serializers.ModelSerializer):
    people = serializers.SerializerMethodField()
    gedcom_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Tree
        fields = ['user', 'id', 'name', 'description', 'upload_date', 'private', 'people', 'gedcom_file']
        read_only_fields = ['id', 'upload_date', 'people']

    def get_people(self, obj):
        return Person.objects.filter(tree=obj).count()

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Tree name is required.")
        return value.strip()