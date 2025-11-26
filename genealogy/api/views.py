from rest_framework.views import APIView
from rest_framework.response import Response

from genealogy.models import Tree
from .serializers import TreeSerializer

class TreeView(APIView):
    def get(self, request):
        queryset = Tree.objects.all()
        serializer = TreeSerializer(queryset, many=True)
        return Response(serializer.data)