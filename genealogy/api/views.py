from django.db.models import Q, OuterRef, Subquery, PositiveSmallIntegerField
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from genealogy.constants import NAMES_REPLACE, SURNAMES_REPLACE
from genealogy.models import Person, Tree, Family, Child, Event, Image, ImagePerson
from genealogy import gedcom
from genealogy.views.common import get_default_image, get_profile_photo
from .serializers import PersonSearchSerializer, PersonSerializer, TreeSerializer

from functools import reduce

class PersonViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonSerializer
    
    def get_queryset(self):
        return Person.objects.filter(
            tree__id=self.kwargs["tree_pk"],
            tree__user=self.request.user,
        )
    
    @action(detail=True, methods=['get'])
    def images(self, request, tree_pk=None, pk=None):
        """Get all images for a person"""
        person = self.get_object()
        image_persons = ImagePerson.objects.filter(person=person).select_related('image')
        
        images_data = []
        for ip in image_persons:
            images_data.append({
                'id': ip.image.id,
                'title': ip.image.title,
                'description': ip.image.description,
                'image_url': ip.image.image.url,
                'created': ip.image.created,
                'is_profile': person.profile_image == ip.image if person.profile_image else False
            })
        
        return Response(images_data)
    
    @action(detail=True, methods=['post'])
    def upload_image(self, request, tree_pk=None, pk=None):
        """Upload a new image for a person"""
        person = self.get_object()
        tree = person.tree
        
        if not request.FILES.get('image'):
            return Response(
                {"error": "No image file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        title = request.data.get('title', f'Image of {person.get_name()}')
        description = request.data.get('description', '')
        
        # Create image
        image = Image.objects.create(
            user=request.user,
            tree=tree,
            title=title,
            description=description,
            image=request.FILES['image'],
            private=False
        )
        
        # Link image to person
        ImagePerson.objects.create(person=person, image=image)
        
        return Response({
            'id': image.id,
            'title': image.title,
            'description': image.description,
            'image_url': image.image.url,
            'created': image.created,
            'is_profile': False
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='delete_image/(?P<image_id>[^/.]+)')
    def delete_image(self, request, tree_pk=None, pk=None, image_id=None):
        """Delete an image"""
        person = self.get_object()
        
        try:
            image = Image.objects.get(id=image_id, tree=person.tree, user=request.user)
        except Image.DoesNotExist:
            return Response(
                {"error": "Image not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # If this is the profile image, clear it
        if person.profile_image == image:
            person.profile_image = None
            person.save()
        
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['patch'], url_path='set_profile_image/(?P<image_id>[^/.]+)')
    def set_profile_image(self, request, tree_pk=None, pk=None, image_id=None):
        """Set an image as profile picture"""
        person = self.get_object()
        
        try:
            image = Image.objects.get(id=image_id, tree=person.tree)
            # Check if image is linked to this person
            ImagePerson.objects.get(person=person, image=image)
        except (Image.DoesNotExist, ImagePerson.DoesNotExist):
            return Response(
                {"error": "Image not found or not linked to this person"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        person.profile_image = image
        person.save()
        
        return Response({
            'message': 'Profile image set successfully',
            'profile_image': image.image.url
        })
    
    @action(detail=True, methods=['post', 'patch'], url_path='update_event/(?P<event_type>[^/.]+)')
    def update_event(self, request, tree_pk=None, pk=None, event_type=None):
        """Create or update a birth/death event"""
        person = self.get_object()
        
        if event_type not in ['birth', 'death']:
            return Response(
                {"error": "Event type must be 'birth' or 'death'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        date = request.data.get('date', '')
        place = request.data.get('place', '')
        
        # Get or create the event
        event, created = Event.objects.get_or_create(
            person=person,
            event_type=event_type,
            defaults={
                'date': date,
                'place': place
            }
        )
        
        # Update if it already existed
        if not created:
            event.date = date
            event.place = place
            event.save()
        
        return Response({
            'message': f'{event_type.capitalize()} event {"created" if created else "updated"} successfully',
            'event': {
                'type': event_type,
                'date': event.date,
                'place': event.place
            }
        })


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

        serializer = PersonSearchSerializer(queryset, many=True)
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
    
    @action(detail=True, methods=['get'], url_path='view/(?P<person_pk>[^/.]+)')
    def tree_view(self, request, pk=None, person_pk=None):
        """
        Get tree data for visualization
        Returns: Tree data with family structure for the specified person
        """
        tree = self.get_object()
        
        # Get person count
        person_count = Person.objects.filter(tree=tree).count()
        
        # If no people in tree
        if person_count == 0:
            return Response({
                'tree_id': tree.id,
                'tree_name': tree.name,
                'person_count': 0,
                'tree_data': None
            })
        
        # If person_pk is 0, get the first person
        if person_pk == '0':
            first_person = Person.objects.filter(tree=tree).order_by('id').first()
            if not first_person:
                return Response({
                    'tree_id': tree.id,
                    'tree_name': tree.name,
                    'person_count': 0,
                    'tree_data': None
                })
            person_pk = first_person.id
        
        # Get the specified person
        try:
            first_person = Person.objects.get(pk=person_pk, tree=tree)
        except Person.DoesNotExist:
            return Response(
                {"error": "Person not found in this tree"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build tree data
        generations = 3
        people_data = self._get_person_tree_data(first_person, tree.id)
        people_data['parents'] = self._tree_get_parents(first_person, 1, generations, tree.id)
        
        # Get partner and children
        family = Family.objects.filter(Q(husband=first_person) | Q(wife=first_person)).first()
        if family:
            if family.husband == first_person and family.wife:
                people_data['partner'] = self._get_person_tree_data(family.wife, tree.id)
            elif family.wife == first_person and family.husband:
                people_data['partner'] = self._get_person_tree_data(family.husband, tree.id)
            
            # Get children
            birth_year_subquery = Event.objects.filter(
                person=OuterRef('person'), 
                event_type='birth'
            ).values('year')[:1]
            
            children = Child.objects.filter(family=family).annotate(
                birth_year=Subquery(birth_year_subquery, output_field=PositiveSmallIntegerField())
            ).order_by('birth_year')
            
            if children:
                people_data['children'] = []
                for child in children:
                    people_data['children'].append(self._get_person_tree_data(child.person, tree.id))
        
        return Response({
            'tree_id': tree.id,
            'tree_name': tree.name,
            'person_count': person_count,
            'tree_data': people_data
        })
    
    def _get_person_tree_data(self, person, tree_id):
        """Helper method to get person data for tree visualization"""
        return {
            'first_name': person.first_name,
            'last_name': person.last_name,
            'id': person.id,
            'image': get_default_image(person.sex) if not person.profile_image else get_profile_photo(person),
            'years': person.get_years(),
            'person_url': f'/tree/{tree_id}/person/{person.id}',
            'tree_url': f'/tree/{tree_id}/person/{person.id}',
        }
    
    def _tree_get_parents(self, current_person, generation, max_generation, tree_id):
        """Helper method to recursively get parents"""
        if generation == max_generation:
            return []
        
        parents = []
        father = current_person.get_father()
        mother = current_person.get_mother()
        
        if father:
            parents.append({
                'first_name': father.first_name,
                'last_name': father.last_name,
                'id': father.id,
                'image': get_default_image(father.sex) if not father.profile_image else get_profile_photo(father),
                'years': father.get_years(),
                'person_url': f'/tree/{tree_id}/person/{father.id}',
                'tree_url': f'/tree/{tree_id}/person/{father.id}',
                'parent_type': 'father',
                'parents': self._tree_get_parents(father, generation + 1, max_generation, tree_id)
            })
        else:
            parents.append({
                'id': 0,
                'child_id': current_person.id,
                'person_url': f'/api/genealogy/person/{current_person.id}/add-parent/father',
                'parent_type': 'father',
                'parents': []
            })
        
        if mother:
            parents.append({
                'first_name': mother.first_name,
                'last_name': mother.last_name,
                'id': mother.id,
                'image': get_default_image(mother.sex) if not mother.profile_image else get_profile_photo(mother),
                'years': mother.get_years(),
                'person_url': f'/tree/{tree_id}/person/{mother.id}',
                'tree_url': f'/tree/{tree_id}/person/{mother.id}',
                'parent_type': 'mother',
                'parents': self._tree_get_parents(mother, generation + 1, max_generation, tree_id)
            })
        else:
            parents.append({
                'id': 0,
                'child_id': current_person.id,
                'person_url': f'/api/genealogy/person/{current_person.id}/add-parent/mother',
                'parent_type': 'mother',
                'parents': []
            })
        
        return parents