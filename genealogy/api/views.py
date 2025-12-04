from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from genealogy.models import Tree
from .serializers import TreeSerializer

class TreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Tree.objects.all().filter(user=request.user)
        serializer = TreeSerializer(queryset, many=True)
        return Response(serializer.data)