from rest_framework import serializers
from genealogy.models import Tree

class TreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tree
        fields = ['name', 'description']