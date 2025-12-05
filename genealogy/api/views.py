from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from genealogy.models import Tree
from genealogy import gedcom
from .serializers import TreeSerializer

class TreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Tree.objects.all().filter(user=request.user).order_by('name')
        serializer = TreeSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # request.user is automatically set by IsAuthenticated
        data = request.data.copy()  # mutable copy
        data['user'] = request.user.id  # attach current user

        serializer = TreeSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create the tree instance (but don't save yet)
        tree = serializer.save()

        # Handle GEDCOM file if uploaded
        gedcom_file = request.FILES.get('gedcom_file')
        if gedcom_file:
            tree.gedcom_file = gedcom_file
            tree.save()  # Save again so file is stored

            # Parse the GEDCOM and populate the tree
            try:
                gedcom.handle_uploaded_file(tree)  # Your existing parser function
            except Exception as e:
                # Optional: delete tree if parsing fails?
                tree.delete()
                return Response(
                    {"error": "GEDCOM file is invalid or corrupted.", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(TreeSerializer(tree).data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, pk=None):
        tree = get_object_or_404(Tree, id=pk, user=request.user)
        tree.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def patch(self, request, pk=None):
        tree = get_object_or_404(Tree, id=pk, user=request.user)
        serializer = TreeSerializer(tree, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)