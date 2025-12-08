from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from genealogy.models import Person, Tree
from genealogy import gedcom
from .serializers import PersonSerializer, TreeSerializer

class PersonView(ModelViewSet):
    permission_classes = [IsAuthenticated]

class PersonSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tree = request.query_params.get('tree')
        queryset = Person.objects.filter(tree=tree).order_by('last_name')

        first_name = request.query_params.get('first_name')
        last_name = request.query_params.get('last_name')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)

        serializer = PersonSerializer(queryset, many=True)
        return Response(serializer.data)
    
class TreeViewSet(ModelViewSet):
    serializer_class = TreeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Tree.objects.filter(user=self.request.user).order_by('name')

    def create(self, request, *args, **kwargs):
        """
        Custom create to handle GEDCOM file upload and parsing
        """
        # Make data mutable
        data = request.data.copy()
        data['user'] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Save the tree (without GEDCOM first)
        tree = serializer.save()

        # Handle GEDCOM file if provided
        gedcom_file = request.FILES.get('gedcom_file')
        if gedcom_file:
            tree.gedcom_file = gedcom_file
            tree.save(update_fields=['gedcom_file'])  # Save file

            try:
                gedcom.handle_uploaded_file(tree)
            except Exception as e:
                # Optional: delete tree on parse failure?
                tree.delete()
                return Response(
                    {"error": "GEDCOM processing failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        """
        Optional: clean up GEDCOM file on delete
        """
        if instance.gedcom_file:
            instance.gedcom_file.delete(save=False)
        instance.delete()