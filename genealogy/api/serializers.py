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
        if len(value.strip()) > 100:
            raise serializers.ValidationError("Tree name cannot exceed 100 characters.")
        return value.strip()
    
class PersonSearchSerializer(serializers.ModelSerializer):
    birth_year = serializers.SerializerMethodField()
    death_year = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'birth_year', 'death_year', 'tree']

    def get_birth_year(self, obj):
        return obj.get_birth_year()
    
    def get_death_year(self, obj):
        return obj.get_death_year()
    
class PersonSerializer(serializers.ModelSerializer):
    birth = serializers.SerializerMethodField()
    death = serializers.SerializerMethodField()
    years = serializers.SerializerMethodField()
    relatives = serializers.SerializerMethodField()
    sex = serializers.CharField(source='get_sex_display', read_only=True)

    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'tree', 'sex', 'birth', 'death', 'years', 'relatives']

    def get_birth(self, obj):
        return obj.get_birth_data()
    
    def get_death(self, obj):
        return obj.get_death_data()
    
    # To fix: combine with other birth/death data to avoid multiple Event lookups
    def get_years(self, obj):
        return obj.get_years()
    
    def get_relatives(self, obj):
        return obj.get_family_data()
