from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from genealogy.constants import NAMES_REPLACE, SURNAMES_REPLACE
from genealogy.models import Person, Tree
from genealogy import gedcom
from .serializers import PersonSerializer, TreeSerializer

from functools import reduce

class PersonView(ModelViewSet):
    permission_classes = [IsAuthenticated]

class PersonSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tree = request.query_params.get('tree')

        first_name = request.query_params.get('first_name')
        last_name = request.query_params.get('last_name')
        birth_place = request.query_params.get('birth_place')
        death_place = request.query_params.get('death_place')
        birth_year = request.query_params.get('birth_year')
        death_year = request.query_params.get('death_year')
        birth_year_from = request.query_params.get('birth_year_from')
        birth_year_to = request.query_params.get('birth_year_to')
        death_year_from = request.query_params.get('death_year_from')
        death_year_to = request.query_params.get('death_year_to')

        name_conditions = []
        birth_conditions = []
        death_conditions = []

        if first_name:
            name_strings = first_name.split()
            name_or_conditions = []
            for name in name_strings:
                found_first = False
                for n in NAMES_REPLACE:
                    if name in n:
                        found_first = True
                        for variation in n:
                            name_or_conditions.append(Q(first_name__icontains=variation))
                if not found_first:    
                    name_or_conditions.append(Q(first_name__icontains=name))
            name_or_conditions = reduce(lambda x, y: x | y, name_or_conditions)
            if name_conditions:
                name_conditions = name_conditions & name_or_conditions
            else:
                name_conditions = name_or_conditions

        if last_name:
            name_strings = last_name.split()
            name_or_conditions = []
            for name in name_strings:
                found_last = False
                for n in SURNAMES_REPLACE:
                    if name in n:
                        found_last = True
                        for variation in n:
                            name_or_conditions.append(Q(last_name__icontains=variation))
                if not found_last:
                    name_or_conditions.append(Q(last_name__icontains=name))
            name_or_conditions = reduce(lambda x, y: x | y, name_or_conditions)
            if name_conditions:
                name_conditions = name_conditions & name_or_conditions
            else:
                name_conditions = name_or_conditions
        
        if birth_place:
            birth_conditions.append(Q(event__place__icontains=birth_place))
        if birth_year:
            birth_conditions.append(Q(event__date__icontains=birth_year))
        if birth_year_from:
            birth_conditions.append(Q(event__year__gte=birth_year_from))
        if birth_year_to:
            birth_conditions.append(Q(event__year__lte=birth_year_to))
        if death_place:
            death_conditions.append(Q(event__place__icontains=death_place))
        if death_year:
            death_conditions.append(Q(event__date__icontains=death_year))
        if death_year_from:
            death_conditions.append(Q(event__year__gte=death_year_from))
        if death_year_to:
            death_conditions.append(Q(event__year__lte=death_year_to))

        final_query = Q(tree=tree)
        if name_conditions:
            final_query = final_query & name_conditions

        queryset = Person.objects.filter(final_query)

        if birth_conditions:
            birth_query = Q(event__event_type='birth') & reduce(lambda x, y: x & y, birth_conditions)
            queryset = queryset.filter(birth_query)
        if death_conditions:
            death_query = Q(event__event_type='death') & reduce(lambda x, y: x & y, death_conditions)
            queryset = queryset.filter(death_query)

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