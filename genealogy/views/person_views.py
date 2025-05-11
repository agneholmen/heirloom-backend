from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, PositiveSmallIntegerField, Q, Subquery
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from itertools import chain

from .common import *

from ..forms import (
    AddEventForm,
    AddExistingPersonChildForm,
    AddFamilyEventForm,
    EditEventForm, 
    EditFamilyEventForm, 
    EventShortForm, 
    ExistingChildrenForm,
    FindExistingPersonForm,
    ImageAddForm,
    ImageCommentAddForm,
    ImageEditForm,
    PersonNamesFamilyForm,
    PersonNamesForm,
    RemoveRelationshipForm,
    SelectEventForm
)
from ..models import (
    Child, 
    Event, 
    Family, 
    FamilyEvent,
    Image,
    ImageComment,
    ImageLike,
    ImagePerson,
    Person,
    Tree
)

from ..date_functions import extract_year

from functools import reduce

# person/<int:pk>
@login_required
def person(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    birth = this_person.get_birth_event()
    death = this_person.get_death_event()

    # Used for sorting siblings, half-siblings, and children based on birth year
    birth_year_subquery = Event.objects.filter(person=OuterRef('person'), event_type='birth').values('year')[:1]

    father = this_person.get_father()
    mother = this_person.get_mother()
    siblings = None
    half_siblings = None
    families = None
    children_objects = Child.objects.filter(person=this_person)
    if children_objects:
        siblings = Child.objects.filter(family=children_objects[0].family).exclude(id=children_objects[0].id).annotate(birth_year=Subquery(birth_year_subquery, output_field=PositiveSmallIntegerField())).order_by('birth_year')

        half_sibling_queries = Q()
        if father is not None:
            half_sibling_queries |= Q(husband=father) & ~Q(wife=mother)
        if mother is not None:
            half_sibling_queries |= Q(wife=mother) & ~Q(husband=father)

        half_sibling_families = Family.objects.filter(half_sibling_queries)
        half_siblings = Child.objects.filter(family__in=half_sibling_families).exclude(person=this_person).annotate(birth_year=Subquery(birth_year_subquery, output_field=PositiveSmallIntegerField())).order_by('birth_year')
    
    timeline_events = []
    timeline_events_no_year = []

    family_objects = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person))
    if family_objects:
        families = []
        for f in family_objects:
            family = {
                'partner': None, 
                'children': [],
                'id': f.id
            }

            # Sort children based on birth year
            family['children'] = Child.objects.filter(family=f).annotate(birth_year=Subquery(birth_year_subquery, output_field=PositiveSmallIntegerField())).order_by('birth_year')

            # Add timeline events for children
            for child in family['children']:
                c_birth = child.person.get_birth_event()
                c_death = child.person.get_death_event()
                if c_birth and c_birth.year:
                    timeline_events.append(
                        {
                            'year': c_birth.year, 
                            'description': "", 
                            'date': c_birth.date,
                            'event_type': 'birth', 
                            'event_type_full': f"Birth of {'son' if child.person.sex == 'M' else 'daughter' if child.person.sex == 'F' else 'child'}",
                            'place': c_birth.place, 
                            'id': child.person.id,
                            'model_type': 'relative',
                            'family_member': child.person
                        }
                    )
                if c_death and death and c_death.year and death.year and c_death.year < death.year:
                    timeline_events.append(
                        {
                            'year': c_death.year, 
                            'description': "", 
                            'date': c_death.date,
                            'event_type': 'birth', 
                            'event_type_full': f"Death of {'son' if child.person.sex == 'M' else 'daughter' if child.person.sex == 'F' else 'child'}",
                            'place': c_death.place, 
                            'id': child.person.id,
                            'model_type': 'relative',
                            'family_member': child.person
                        }
                    )

            if f.husband == this_person and f.wife:
                family['partner'] = f.wife
            if f.wife == this_person and f.husband:
                family['partner'] = f.husband
            
            # Add timeline events for partner
            if family['partner']:
                p_death = family['partner'].get_death_event()
                if p_death and death and p_death.year and death.year and p_death.year < death.year:
                    timeline_events.append(
                        {
                            'year': p_death.year, 
                            'description': "", 
                            'date': p_death.date,
                            'event_type': 'death', 
                            'event_type_full': f"Death of {'husband' if family['partner'].sex == 'M' else 'wife' if family['partner'].sex == 'F' else 'partner'}",
                            'place': p_death.place,
                            'id': family['partner'].id,
                            'model_type': 'relative',
                            'family_member': family['partner']
                        }
                    )

            families.append(family)

    events = Event.objects.filter(person=this_person).order_by('year')
    family_events = FamilyEvent.objects.filter(family__in=family_objects).order_by('year')

    for e in events:
        if e.event_type not in ['birth', 'death']:
            new_event = {
                    'year': e.year, 
                    'description': e.description,
                    'date': e.date,
                    'event_type': e.event_type, 
                    'event_type_full': e.get_event_type_display(),
                    'place': e.place, 
                    'id': e.id, 
                    'model_type': 'basic'
                }
            if new_event['year']:
                timeline_events.append(new_event)
            else:
                timeline_events_no_year.append(new_event)
    for e in family_events:
        new_event = {
                'year': e.year, 
                'description': e.description, 
                'date': e.date,
                'event_type': e.event_type, 
                'event_type_full': e.get_event_type_display(),
                'family_member': e.family.husband if e.family.wife == this_person else e.family.wife,
                'place': e.place, 
                'id': e.id, 
                'model_type': 'family'
            }
        if new_event['year']:
            timeline_events.append(new_event)
        else:
            timeline_events_no_year.append(new_event)

    # Add events related to relatives
    for s in chain(siblings or [], half_siblings or []):
        s_birth = s.person.get_birth_event()
        s_death = s.person.get_death_event()
        if s_birth and birth and s_birth.year and birth.year and s_birth.year > birth.year and not (death and death.year and s_birth.year > death.year):
            timeline_events.append(
                {
                    'year': s_birth.year, 
                    'description': "", 
                    'date': s_birth.date,
                    'event_type': 'birth', 
                    'event_type_full': f"Birth of {'brother' if s.person.sex == 'M' else 'sister' if s.person.sex == 'F' else 'sibling'}",
                    'place': s_birth.place, 
                    'id': s.person.id,
                    'model_type': 'relative',
                    'family_member': s.person
                }
            )
        if s_death and death and s_death.year and death.year and s_death.year < death.year and not (birth and s_death.year < birth.year):
            timeline_events.append(
                {
                    'year': s_death.year, 
                    'description': "", 
                    'date': s_death.date,
                    'event_type': 'death', 
                    'event_type_full': f"Death of {'brother' if s.person.sex == 'M' else 'sister' if s.person.sex == 'F' else 'sibling'}",
                    'place': s_death.place,
                    'id': s.person.id,
                    'model_type': 'relative',
                    'family_member': s.person
                }
            )

    if father:
        f_death = father.get_death_event()
        if not (f_death and death and f_death.year and death.year and f_death.year > death.year) and f_death and f_death.year:
            timeline_events.append(
                {
                    'year': f_death.year, 
                    'description': "", 
                    'date': f_death.date,
                    'event_type': 'death', 
                    'event_type_full': "Death of father",
                    'place': f_death.place,
                    'id': father.id,
                    'model_type': 'relative',
                    'family_member': father
                }
            )
    if mother:
        m_death = mother.get_death_event()
        if not (m_death and death and m_death.year and death.year and m_death.year > death.year) and m_death and m_death.year:
            timeline_events.append(
                {
                    'year': m_death.year,
                    'description': "", 
                    'date': m_death.date,
                    'event_type': 'death', 
                    'event_type_full': "Death of mother",
                    'place': m_death.place,
                    'id': mother.id,
                    'model_type': 'relative',
                    'family_member': mother
                }
            )

    timeline_events.sort(key=lambda x: x['year'])
    if birth:
        timeline_events.insert(0, 
                               {'year': birth.year, 
                                'date': birth.date,
                                'description': birth.description, 
                                'event_type': 'birth',
                                'event_type_full': 'Birth', 
                                'place': birth.place, 
                                'id': birth.id, 
                                'model_type': 'basic'
                                }
                            )
    if death:
        timeline_events.append(
            {
                'year': death.year, 
                'date': death.date,
                'description': death.description, 
                'event_type': 'death', 
                'event_type_full': 'Death',
                'place': death.place, 
                'id': death.id, 
                'model_type': 'basic'
            }
        )

    timeline_events.extend(timeline_events_no_year)

    # More should be added
    for event in timeline_events:
        if event['event_type'] == 'birth':
            event['icon'] = '🎂'
        elif event['event_type'] == 'baptism':
            event['icon'] = '🕊️'
        elif event['event_type'] == 'death':
            event['icon'] = '☠️'
        elif event['event_type'] == 'funeral':
            event['icon'] = '⚰️'
        elif event['event_type'] == 'marriage':
            event['icon'] = '💍'
        elif event['event_type'] == 'residence':
            event['icon'] = '🏠'
        elif event['event_type'] == 'divorce':
            event['icon'] = '💔'
        else:
            event['icon'] = '📆'

    has_images = Image.objects.filter(id__in=ImagePerson.objects.filter(person=this_person).values('image')).exists()

    return render(
        request,
        'genealogy/person.html',
        {
            'section': 'search',
            'person': this_person,
            'default_image': None if this_person.profile_image else get_default_image(this_person.sex),
            'profile_photo': this_person.profile_image if this_person.profile_image else None,
            'birth': birth,
            'death': death,
            'father': father,
            'mother': mother,
            'siblings': siblings,
            'half_siblings': half_siblings,
            'families': families,
            'events': timeline_events,
            'has_images': has_images
        }
    )

# person/<int:pk>/edit/person
@login_required
@transaction.atomic
def edit_person(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == 'POST':
        person_form = PersonNamesForm(instance=this_person, data=request.POST)
        birth_form = EventShortForm(instance=Event.get_or_new(this_person, 'birth'), data=request.POST, prefix='birth')
        death_form = EventShortForm(instance=Event.get_or_new(this_person, 'death'), data=request.POST, prefix='death')

        if not person_form.is_valid():
            response = JsonResponse({'errors': dict(person_form.errors)}, status=400)
            return response
        if not birth_form.is_valid():
            response = JsonResponse({'errors': dict(birth_form.errors)}, status=400)
            return response
        if not death_form.is_valid():
            response = JsonResponse({'errors': dict(death_form.errors)}, status=400)
            return response

        person_form.save()
        bf_data = birth_form.cleaned_data
        if bf_data['date'] or bf_data['place']:
            birth_form.save()
        elif not bf_data['date'] and not bf_data['place'] and not birth_form.instance.description and birth_form.instance.pk:
            birth_form.instance.delete()
        df_data = death_form.cleaned_data
        if df_data['date'] or df_data['place']:
            death_form.save()
        elif not df_data['date'] and not df_data['place'] and not death_form.instance.description and death_form.instance.pk:
            death_form.instance.delete()
        response = HttpResponse(status=204)
        response.headers = {'HX-Trigger': f'update-person-{str(pk)}'}
        return response
    else:
        person_form = PersonNamesForm(instance=this_person)
        birth_form = EventShortForm(instance=Event.get_or_new(this_person, 'birth'), prefix='birth')
        death_form = EventShortForm(instance=Event.get_or_new(this_person, 'death'), prefix='death')

    return render(
        request, 
        'genealogy/edit_person_modal.html',
        {
            'person_form': person_form,
            'birth_form': birth_form,
            'death_form': death_form
        }
    )

# person/<int:pk>/edit/relationships
@login_required
@transaction.atomic
def edit_relationships(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == 'POST':
        used_form = RemoveRelationshipForm(request.POST)

        if used_form.is_valid():
            cd = used_form.cleaned_data
            if cd['relationship_type'] == 'father':
                this_child = Child.objects.get(person=this_person, family__husband=cd['related_person_id'])
                if this_child.family.wife:
                    try:
                        wife_family = Family.objects.get(wife=this_child.family.wife, husband=None)
                        this_child.family = wife_family
                        this_child.save()
                    except:
                        wife_family = Family()
                        wife_family.wife = this_child.family.wife
                        wife_family.tree = this_child.family.tree
                        wife_family.save()
                        this_child.family = wife_family
                        this_child.save()
                else:
                    this_child.delete()

            elif cd['relationship_type'] == 'mother':
                this_child = Child.objects.get(person=this_person, family__wife=cd['related_person_id'])
                if this_child.family.husband:
                    try:
                        husband_family = Family.objects.get(husband=this_child.family.husband, wife=None)
                        this_child.family = husband_family
                        this_child.save()
                    except:
                        husband_family = Family()
                        husband_family.husband = this_child.family.husband
                        husband_family.tree = this_child.family.tree
                        husband_family.save()
                        this_child.family = husband_family
                        this_child.save()
                else:
                    this_child.delete()
            elif cd['relationship_type'] == 'child':
                this_child = Child.objects.get(Q(person=cd['related_person_id']) & (Q(family__husband=this_person) | Q(family__wife=this_person)))
                if (this_child.family.wife == this_person and not this_child.family.husband) \
                    or (this_child.family.husband == this_person and not this_child.family.wife):
                    if this_child.family.children.count() == 1:
                        this_child.family.delete()
                    else:
                        this_child.delete()
                else:
                    if this_child.family.husband == this_person:
                        try:
                            wife_family = Family.objects.get(wife=this_child.family.wife, husband=None)
                            this_child.family = wife_family
                            this_child.save()
                        except:
                            wife_family = Family()
                            wife_family.wife = this_child.family.wife
                            wife_family.tree = this_child.family.tree
                            wife_family.save()
                            this_child.family = wife_family
                            this_child.save()
                    else:
                        try:
                            husband_family = Family.objects.get(husband=this_child.family.husband, wife=None)
                            this_child.family = husband_family
                            this_child.save()
                        except:
                            husband_family = Family()
                            husband_family.husband = this_child.family.husband
                            husband_family.tree = this_child.family.tree
                            husband_family.save()
                            this_child.family = husband_family
                            this_child.save()
            elif cd['relationship_type'] == 'partner':
                this_family = Family.objects.get(Q(husband=this_person) | Q(wife=this_person), Q(husband=cd['related_person_id']) | Q(wife=cd['related_person_id']))
                if this_family.children.count() == 0:
                    this_family.delete()
                else:
                    response = JsonResponse({'errors': {'have_children': 'Cannot remove partner since they have children together!'}}, status=400)
                    return response
            else:
                response = JsonResponse({'errors': {'relationship_type': 'Invalid relationship type!'}}, status=400)
                return response
            
            response = HttpResponse(status=204)
            return response

        else:
            response = JsonResponse({'errors': dict(used_form.errors)}, status=400)
            return response
    else:
        father = this_person.get_father()
        mother = this_person.get_mother()
        father_form = None
        mother_form = None
        children_forms = []
        partner_forms = []
        children_objects = Child.objects.filter(person=this_person)
        if children_objects:
            if father:
                father_form = RemoveRelationshipForm(initial={'relationship_type': 'father', 'related_person_id': father.id})
            if mother:
                mother_form = RemoveRelationshipForm(initial={'relationship_type': 'mother', 'related_person_id': mother.id})

        children = Child.objects.filter(Q(family__husband=this_person) | Q(family__wife=this_person))
        for c in children:
            child_form = RemoveRelationshipForm(initial={'relationship_type': 'child', 'related_person_id': c.person.id})
            children_forms.append((c.person, child_form))
        families = Family.objects.filter((Q(husband=this_person) & ~Q(wife=None)) | (Q(wife=this_person) & ~Q(husband=None)))
        for f in families:
            if f.husband == this_person:
                partner_form = RemoveRelationshipForm(initial={'relationship_type': 'partner', 'related_person_id': f.wife.id})
                partner_forms.append((f.wife, partner_form))
            else:
                partner_form = RemoveRelationshipForm(initial={'relationship_type': 'partner', 'related_person_id': f.husband.id})
                partner_forms.append((f.husband, partner_form))

    return render(
        request,
        'genealogy/edit_relationships_modal.html',
        {
            'father_form': father_form,
            'mother_form': mother_form,
            'father': father,
            'mother': mother,
            'partners': partner_forms,
            'children': children_forms,
            'person': this_person
        }
    )

# person/<int:pk>/delete
@login_required
@transaction.atomic
def delete_person(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == "POST":
        referer_url = request.META.get('HTTP_REFERER')
        # Need to redirect to different person if deleting from person page
        if 'person/' in referer_url:
            related_person = find_close_relative(this_person)

        try:
            this_person.delete()
            messages.success(
                request,
                "Person successfully removed!"
            )
            if 'person/' in referer_url:
                if related_person:
                    # Apparently the URL is not updated when using HX-Request so this fix is needed. Stupid...
                    if "HX-Request" in request.headers:
                        new_url = reverse('genealogy:person', kwargs={'pk': related_person.id})
                        response = JsonResponse({})
                        response['HX-Redirect'] = new_url
                        return response
                    else:
                        return redirect(new_url)
                else:
                    return redirect('genealogy:tree', pk=this_person.tree.id)
            else:
                return HttpResponse(status=204)
        except:
            messages.error(request, "There was a problem removing the person!")
            return HttpResponse(status=400)
    else:
        return render(request, 'genealogy/delete_person_modal.html', {'person': this_person})

# person/<int:person_pk>/add/partner/<int:family_pk>
@login_required
@transaction.atomic
def add_person_as_partner(request, person_pk, family_pk):
    this_person = get_object_or_404(Person, pk=person_pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_new_person':
            person_form = PersonNamesForm(request.POST)
            birth_form = EventShortForm(request.POST, prefix='birth')
            death_form = EventShortForm(request.POST, prefix='death')
            if 'existing_children' in request.POST:
                existing_children_form = ExistingChildrenForm(request.POST)
                existing_children_form.fields['existing_children'].choices = get_single_parent_children(this_person)
            else:
                existing_children_form = None

            if not person_form.is_valid():
                response = JsonResponse({'errors': dict(person_form.errors)}, status=400)
                return response
            if not birth_form.is_valid():
                response = JsonResponse({'errors': dict(birth_form.errors)}, status=400)
                return response
            if not death_form.is_valid():
                response = JsonResponse({'errors': dict(death_form.errors)}, status=400)
                return response
            if existing_children_form and not existing_children_form.is_valid():
                response = JsonResponse({'errors': dict(existing_children_form.errors)}, status=400)
                return response

            cd = person_form.cleaned_data

            partner = Person()
            partner.tree = this_person.tree
            partner.first_name = cd['first_name']
            partner.last_name = cd['last_name']
            partner.sex = cd['sex']
            partner.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(person=partner, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(person=partner, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            # No existing children to add to new partner
            if not existing_children_form or (existing_children_form and not existing_children_form.cleaned_data['existing_children']) or family_pk != 0:
                try:
                    family = Family.objects.get(pk=family_pk)
                    if this_person.sex == 'M':
                        family.husband = this_person
                        family.wife = partner
                    else:
                        family.husband = partner
                        family.wife = this_person
                    family.save()
                except:
                    family = Family()
                    if this_person.sex == 'M':
                        family.husband = this_person
                        family.wife = partner
                    else:
                        family.husband = partner
                        family.wife = this_person
                    family.tree = this_person.tree
                    family.save()
            elif existing_children_form:
                selected_children = existing_children_form.cleaned_data['existing_children']
                families = Family.objects.filter((Q(husband=this_person) & Q(wife=None)) | (Q(wife=this_person) & Q(husband=None)))
                if families:
                    # This should not be needed, but updating families[0] directly doesn't work for some reason.
                    family = Family.objects.get(id=families[0].id)

                    if this_person.sex == 'M':
                        family.husband = this_person
                        family.wife = partner
                    else:
                        family.husband = partner
                        family.wife = this_person
                    family.save()

                # Create new single parent family for remaining children
                if len(selected_children) != len(existing_children_form.fields['existing_children'].choices):
                    still_single_parent_children = [child[0] for child in existing_children_form.fields['existing_children'].choices if child[0] not in selected_children]

                    family = Family()
                    if this_person.sex == 'M':
                        family.husband = this_person
                    else:
                        family.wife = this_person
                    family.tree = this_person.tree
                    family.save()

                    for child in still_single_parent_children:
                        child_object = Child.objects.get(id=child)
                        child_object.family = family
                        child_object.save()          

            return HttpResponse(status=204)
            
        elif request.POST.get('identifier') == 'add_existing_person':
            find_people_form = FindExistingPersonForm(request.POST, tree_id=this_person.tree.id)
            if 'existing_children' in request.POST:
                existing_children_form = ExistingChildrenForm(request.POST)
                existing_children_form.fields['existing_children'].choices = get_single_parent_children(this_person)
            else:
                existing_children_form = None
            dropdown_persons = get_dropdown_persons(request.POST.get('person'), this_person.tree.id)
            for p in dropdown_persons:
                find_people_form.fields['selected_person'].choices.append((p.id, p.get_name_years()))

            if existing_children_form and not existing_children_form.is_valid():
                response = JsonResponse({'errors': dict(existing_children_form.errors)}, status=400)
                return response

            if find_people_form.is_valid():
                cd = find_people_form.cleaned_data
                if cd['selected_person'].isnumeric() == False:
                    errors = {'no_partner_selected': 'You did not select a partner!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                try:
                    partner = Person.objects.get(id=cd['selected_person'])
                except Person.DoesNotExist:
                    raise Http404("Person does not exist.")
                
                if Family.objects.filter((Q(wife=this_person) & Q(husband=partner)) | (Q(wife=partner) & Q(husband=this_person))).exists():
                    errors = {'already_a_family': 'The selected people already have a family!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                if (this_person.get_birth_year() and partner.get_death_year() and this_person.get_birth_year() > partner.get_death_year()) \
                    or (this_person.get_death_year() and partner.get_birth_year() and partner.get_birth_year() > this_person.get_death_year()):
                    errors = {'not_alive_at_the_same_time': 'The selected people were not alive at the same time!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                if not existing_children_form or (existing_children_form and not existing_children_form.cleaned_data['existing_children']) or family_pk != 0:
                    try:
                        family = Family.objects.get(id=family_pk)
                        if this_person.sex == 'M':
                            family.husband = this_person
                            family.wife = partner
                        else:
                            family.husband = partner
                            family.wife = this_person
                        family.save()
                    except:
                        family = Family()
                        if this_person.sex == 'M':
                            family.husband = this_person
                            family.wife = partner
                        else:
                            family.husband = partner
                            family.wife = this_person
                        family.tree = this_person.tree
                        family.save()

                elif existing_children_form:
                    selected_children = existing_children_form.cleaned_data['existing_children']
                    families = Family.objects.filter((Q(husband=this_person) & Q(wife=None)) | (Q(wife=this_person) & Q(husband=None)))

                    if families:
                        # This should not be needed, but updating families[0] directly doesn't work for some reason.
                        family = Family.objects.get(id=families[0].id)

                        if this_person.sex == 'M':
                            family.husband = this_person
                            family.wife = partner
                        else:
                            family.husband = partner
                            family.wife = this_person
                        family.save()

                    # Create new single parent family for remaining children
                    if len(selected_children) != len(existing_children_form.fields['existing_children'].choices):
                        still_single_parent_children = [child[0] for child in existing_children_form.fields['existing_children'].choices if child[0] not in selected_children]

                        family = Family()
                        if this_person.sex == 'M':
                            family.husband = this_person
                        else:
                            family.wife = this_person
                        family.tree = this_person.tree
                        family.save()

                        for child in still_single_parent_children:
                            child_object = Child.objects.get(id=child)
                            child_object.family = family
                            child_object.save()

                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(find_people_form.errors)}, status=400)
                return response

    else:
        person_form = PersonNamesForm()
        person_form.fields['identifier'].initial = 'add_new_person'
        birth_form = EventShortForm(prefix='birth')
        death_form = EventShortForm(prefix='death')
        existing_children = get_single_parent_children(this_person)
        if existing_children and family_pk == 0:
            existing_children_form = ExistingChildrenForm()
            existing_children_form.fields['existing_children'].choices = existing_children
            existing_children_form.fields['existing_children'].initial = [child[0] for child in existing_children]
        else:
            existing_children_form = None
        find_people_form = FindExistingPersonForm(tree_id=this_person.tree.id)

    title = f'Add Partner for {this_person}'

    return render(
        request, 
        'genealogy/add_new_existing_person_modal.html', 
        {
            'person_form': person_form,
            'birth_form': birth_form,
            'death_form': death_form,
            'existing_children_form': existing_children_form,
            'search_form': find_people_form, 
            'modal_title': title
        }
    )

# tree/<int:pk>/find-for-dropdown
@login_required
@require_POST
def search_people_for_dropdown(request, pk):
    query = request.POST.get('person', '')
    persons = get_dropdown_persons(query, pk)

    return render(request, 'genealogy/person_dropdown.html', {'persons': persons})

# person/find-families-for-dropdown
@login_required
@require_POST
def families_for_dropdown(request):
    person = request.POST.get('selected_person', '')
    families = get_families(person)

    return render(request, 'genealogy/family_dropdown.html', {'families': families})

def get_families(person):
    try:
        this_person = Person.objects.get(id=person)
        families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person))
        family_choices = [(family.id, family) for family in families]
        if not Family.objects.filter((Q(husband=this_person) & Q(wife=None)) | (Q(wife=this_person) & Q(husband=None))).exists():
            family_choices.append((0, f'{this_person} and unknown partner'))
    except:
        family_choices = []

    return family_choices

def get_dropdown_persons(query, pk):
    if query:
        db_query_items = []
        query_items = query.split(" ")
        years = []
        for q in query_items:
            if q.isnumeric():
                # If people write more than 2 years, ignore the third and more
                if len(years) < 2:
                    years.append(q)
            else:
                item = (Q(first_name__icontains=q) | Q(last_name__icontains=q))
                db_query_items.append(item)
        # With two years, the queries need to separated
        if len(years) == 2:
            birth_query = (Q(event__event_type='birth') & Q(event__year=min(years)))
            death_query = (Q(event__event_type='death') & Q(event__year=max(years)))
        elif len(years) == 1:
            birth_query = ((Q(event__event_type='birth') & Q(event__year=q)) | (Q(event__event_type='death') & Q(event__year=q)))
        if years:
            db_query_items.append(birth_query)
        tree = Tree.objects.get(pk=pk)
        persons = Person.objects.filter(reduce(lambda x, y: x & y, db_query_items) & Q(tree=tree))
        # If two years included, also search for specific death year
        if len(years) == 2:
            persons = persons.filter(death_query)
        
        # Get first 10 results
        persons = persons[:10]

    else:
        persons = Person.objects.none()

    return persons

# person/<int:pk>/add/child
@login_required
@transaction.atomic
def add_person_as_child(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    families = Family.objects.filter(Q(wife=this_person) | Q(husband=this_person))
    family_choices = [(family.id, family) for family in families]
    if not Family.objects.filter((Q(husband=this_person) & Q(wife=None)) | (Q(wife=this_person) & Q(husband=None))).exists():
        family_choices.append((0, f'{this_person} and unknown partner'))

    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_new_child':
            person_form = PersonNamesFamilyForm(request.POST)
            person_form.fields['family'].choices = family_choices
            birth_form = EventShortForm(request.POST, prefix='birth')
            death_form = EventShortForm(request.POST, prefix='death')

            if not person_form.is_valid():
                response = JsonResponse({'errors': dict(person_form.errors)}, status=400)
                return response
            if not birth_form.is_valid():
                response = JsonResponse({'errors': dict(birth_form.errors)}, status=400)
                return response
            if not death_form.is_valid():
                response = JsonResponse({'errors': dict(death_form.errors)}, status=400)
                return response
            
            cd = person_form.cleaned_data
            child = Person()
            child.tree = this_person.tree
            child.first_name = cd['first_name']
            child.last_name = cd['last_name']
            child.sex = cd['sex']
            child.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(person=child, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(person=child, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            new_child = Child()
            new_child.person = child
            if cd['family'] == 0:
                family = Family()
                if this_person.sex == 'M':
                    family.husband = this_person
                else:
                    family.wife = this_person
                family.tree = this_person.tree
                family.save()
            else:
                family = Family.objects.get(id=cd['family'])
            new_child.family = family
            new_child.save()

            return HttpResponse(status=204)


        elif request.POST.get('identifier') == 'add_existing_person':
            search_form = AddExistingPersonChildForm(request.POST, tree_id=this_person.tree.id)
            search_form.fields['family'].choices = family_choices
            dropdown_persons = get_dropdown_persons(request.POST.get('person'), this_person.tree.id)
            for p in dropdown_persons:
                search_form.fields['selected_person'].choices.append((p.id, p.get_name_years()))
            if search_form.is_valid():
                cd = search_form.cleaned_data
                if cd['selected_person'].isnumeric() == False:
                    errors = {'no_child_selected': 'You did not select a child!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                try:
                    child = Person.objects.get(id=cd['selected_person'])
                except Person.DoesNotExist:
                    raise Http404("Person does not exist.")
                
                if Child.objects.filter(person=child).exists():
                    errors = {'already_a_child': 'The selected person already has parents!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                if cd['family'] == 0:
                    family = Family()
                    if this_person.sex == 'M':
                        family.husband = this_person
                    else:
                        family.wife = this_person
                    family.tree = this_person.tree
                    family.save()
                else:
                    family = Family.objects.get(id=cd['family'])

                new_child = Child()
                new_child.person = child
                new_child.family = family
                new_child.save()

                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(search_form.errors)}, status=400)
                return response

    else:
        person_form = PersonNamesFamilyForm()
        person_form.fields['identifier'].initial = 'add_new_child'
        person_form.fields['family'].choices = family_choices
        birth_form = EventShortForm(prefix='birth')
        death_form = EventShortForm(prefix='death')
        search_form = AddExistingPersonChildForm(tree_id=this_person.tree.id)
        search_form.fields['family'].choices = family_choices

    title = f'Add Child for {this_person}'

    return render(
        request, 
        'genealogy/add_new_existing_person_modal.html', 
        {
            'person_form': person_form,
            'birth_form': birth_form,
            'death_form': death_form,
            'search_form': search_form, 
            'modal_title': title
        }
    )

# person/<int:pk>/add/parent/<str:parent>
@login_required
@transaction.atomic
def add_person_as_parent(request, pk, parent):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    if parent not in ('father', 'mother'):
        raise Http404("Incorrect parent type.") 

    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_new_person':
            person_form = PersonNamesForm(request.POST)
            birth_form = EventShortForm(request.POST, prefix='birth')
            death_form = EventShortForm(request.POST, prefix='death')

            if not person_form.is_valid():
                response = JsonResponse({'errors': dict(person_form.errors)}, status=400)
                return response
            if not birth_form.is_valid():
                response = JsonResponse({'errors': dict(birth_form.errors)}, status=400)
                return response
            if not death_form.is_valid():
                response = JsonResponse({'errors': dict(death_form.errors)}, status=400)
                return response

            cd = person_form.cleaned_data

            new_parent = Person()
            new_parent.tree = this_person.tree
            new_parent.first_name = cd['first_name']
            new_parent.last_name = cd['last_name']
            new_parent.sex = cd['sex']
            new_parent.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(person=new_parent, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(person=new_parent, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            # Basically, already has a parent
            try:
                child = Child.objects.get(person=this_person)
                if parent == 'father' and child.family.wife:
                    child.family.husband = new_parent
                    child.family.save()
                elif parent == 'mother' and child.family.husband:
                    child.family.wife = new_parent
                    child.family.save()
                else:
                    errors = {'parenthood': 'Something went wrong! Does the person already have two parents?'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
            except:
                family = Family()
                family.tree = this_person.tree
                if parent == 'father':
                    family.husband = new_parent
                elif parent == 'mother':
                    family.wife = new_parent
                else:
                    errors = {'parenthood': 'Something went wrong! Does the person already have two parents?'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                family.save()
                new_child = Child()
                new_child.tree = this_person.tree
                new_child.person = this_person
                new_child.family = family
                new_child.save()

            return HttpResponse(status=204)

        elif request.POST.get('identifier') == 'add_existing_person':
            search_form = FindExistingPersonForm(request.POST, tree_id=this_person.tree.id)
            dropdown_persons = get_dropdown_persons(request.POST.get('person'), this_person.tree.id)
            for p in dropdown_persons:
                search_form.fields['selected_person'].choices.append((p.id, p.get_name_years()))
            if search_form.is_valid():
                cd = search_form.cleaned_data
                if cd['selected_person'].isnumeric() == False:
                    errors = {'no_parent_selected': 'You did not select a parent!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                try:
                    new_parent = Person.objects.get(id=cd['selected_person'])
                except Person.DoesNotExist:
                    raise Http404("Person does not exist.")
                
                # Find existing family. If failure, create new family.
                try:
                    child = Child.objects.get(person=this_person)
                    if child.family.husband == new_parent or child.family.wife == new_parent:
                        errors = {'already_a_parent': 'This person is already a parent of the selected child!'}
                        response = JsonResponse({'errors': errors}, status=400)
                        return response
                    
                    if child.family.husband and child.family.wife:
                        errors = {'already_two_parents': 'This person already has two parents!'}
                        response = JsonResponse({'errors': errors}, status=400)
                        return response
                    
                    if parent == 'father' and child.family.husband:
                        errors = {'already_has_father': 'This person already has a father!'}
                        response = JsonResponse({'errors': errors}, status=400)
                        return response

                    if parent == 'mother' and child.family.wife:
                        errors = {'already_has_mother': 'This person already has a mother!'}
                        response = JsonResponse({'errors': errors}, status=400)
                        return response

                    if parent == 'father':
                        try:
                            existing_family = Family.objects.get(Q(husband=new_parent) & Q(wife=child.family.wife))
                            obsolete_wife_family = Family.objects.filter(Q(wife=child.family.wife) & Q(husband=None))
                            if obsolete_wife_family and obsolete_wife_family[0].children.count() == 1:
                                obsolete_wife_family[0].delete()
                            child.family = existing_family
                            child.save()
                        except:
                            child.family.husband = new_parent
                            child.family.save()
                    else:
                        try:
                            existing_family = Family.objects.get(Q(husband=child.family.husband) & Q(wife=new_parent))
                            obsolete_husband_family = Family.objects.filter(Q(husband=child.family.husband) & Q(wife=None))
                            if obsolete_husband_family and obsolete_husband_family[0].children.count() == 1:
                                obsolete_husband_family[0].delete()
                            child.family = existing_family
                            child.save()
                        except:
                            child.family.wife = new_parent
                            child.family.save()

                    return HttpResponse(status=204)

                # No parents yet   
                except:
                    family = Family()
                    if new_parent.sex == 'M':
                        family.husband = new_parent
                    else:
                        family.wife = new_parent
                    family.tree = this_person.tree
                    family.save()

                    new_child = Child()
                    new_child.person = this_person
                    new_child.family = family
                    new_child.save()

                    return HttpResponse(status=204)
                
            else:
                response = JsonResponse({'errors': dict(search_form.errors)}, status=400)
                return response
    else:
        person_form = PersonNamesForm()
        person_form.fields['identifier'].initial = 'add_new_person'
        birth_form = EventShortForm(prefix='birth')
        death_form = EventShortForm(prefix='death')
        search_form = FindExistingPersonForm(tree_id=this_person.tree.id)

    if parent == 'father':
        title = f'Add Father for {this_person}'
        person_form.fields['sex'].initial = 'M'
    else:
        title = f'Add Mother for {this_person}'
        person_form.fields['sex'].initial = 'F'

    return render(
        request, 
        'genealogy/add_new_existing_person_modal.html', 
        {
            'person_form': person_form,
            'birth_form': birth_form,
            'death_form': death_form,
            'search_form': search_form, 
            'modal_title': title
        }
    )

# person/<int:pk>/event-list
@login_required
def event_list(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    if request.method == 'POST':
        form = SelectEventForm(request.POST)
        if form.is_valid():
            event_type = form.cleaned_data['event_type']
            event_type_text = form.get_event_type_text()

            if any(e[0] == event_type for e in Event.EVENT_TYPES):
                if this_person.has_birth_event() and event_type == 'birth':
                    errors = {'has_birth': 'This person already has a birth event.'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                if this_person.has_death_event() and event_type == 'death':
                    errors = {'has_death': 'This person already has a death event.'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                form = AddEventForm()
                return render(request, 'genealogy/add_event_modal.html', {'person': this_person, 'form': form, 'event_type': event_type, event_type_text: event_type_text})
            elif any(e[0] == event_type for e in FamilyEvent.EVENT_TYPES):
                form = AddFamilyEventForm()
                families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person) & Q(husband__isnull=False) & Q(wife__isnull=False))
                if not families:
                    errors = {'no_families': 'No families found for this person. First add a partner before adding family events!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                form.fields['family'].choices = [(family.id, family) for family in families]

                return render(request, 'genealogy/add_event_modal.html', {'person': this_person, 'form': form, 'event_type': event_type, event_type_text: event_type_text})
            else:
                errors = {'event_type': 'Invalid event type!'}
                response = JsonResponse({'errors': errors}, status=400)
                return response

    else:
        form = SelectEventForm()

        return render(
            request,
            'genealogy/event_list.html',
            {'form': form, 'person': this_person}
        )

# person/<int:pk>/event/add/<str:event_type>
@login_required
def add_event(request, pk, event_type):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_event':
            form = AddEventForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                if cd['date'] and this_person.get_birth_year() and extract_year(cd['date']) < this_person.get_birth_year():
                    errors = {'date': 'Event date is before birth date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                if cd['date'] and this_person.get_death_year() and extract_year(cd['date']) > this_person.get_death_year():
                    errors = {'date': 'Event date is after death date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                cd = form.cleaned_data
                event = Event()
                event.person = this_person
                event.event_type = event_type
                event.date = cd['date']
                event.place = cd['place']
                event.description = cd['description']
                event.save()

                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response

        elif request.POST.get('identifier') == 'add_family_event':
            form = AddFamilyEventForm(request.POST)
            families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person) & Q(husband__isnull=False) & Q(wife__isnull=False))
            form.fields['family'].choices = [(family.id, family) for family in families]
            if form.is_valid():
                cd = form.cleaned_data
                if cd['date'] and this_person.get_birth_year() and extract_year(cd['date']) < this_person.get_birth_year():
                    errors = {'date': 'Event date is before birth date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                if cd['date'] and this_person.get_death_year() and extract_year(cd['date']) > this_person.get_death_year():
                    errors = {'date': 'Event date is after death date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                if FamilyEvent.objects.filter(family=cd['family'], event_type=event_type).exists():
                    errors = {'already_event': f'This family already has a {event_type} event!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                event = FamilyEvent()
                event.family = Family.objects.get(id=cd['family'])
                event.event_type = event_type
                event.date = cd['date']
                event.place = cd['place']
                event.description = cd['description']
                event.save()

                return HttpResponse(status=204)
                
            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
    else:
        print("EPIC FAIL")

# event/<int:pk>/edit
@login_required
def edit_event(request, pk):
    if request.method == 'POST':
        event = Event.objects.get(pk=pk)
        form = EditEventForm(request.POST, instance=event)
        if 'submit' in request.POST:
            if form.is_valid():
                form.save()
                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
        elif 'delete' in request.POST:
            event.delete()
            return HttpResponse(status=204)
        else:
            print("EPIC FAIL")
    else:
        event = Event.objects.get(pk=pk)
        form = EditEventForm(instance=event)

    return render(
        request,
        'genealogy/edit_event_modal.html',
        {
            'form': form, 
            'event': event,
            'event_type_text': event.get_event_type_display()
        }
    )

# family-event/<int:pk>/edit
@login_required
def edit_family_event(request, pk):
    if request.method == 'POST':
        event = FamilyEvent.objects.get(pk=pk)
        form = EditFamilyEventForm(request.POST, instance=event)
        if 'submit' in request.POST:
            if form.is_valid():
                form.save()
                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
        elif 'delete' in request.POST:
            event.delete()
            return HttpResponse(status=204)
        else:
            print("EPIC FAIL")
    else:
        event = FamilyEvent.objects.get(pk=pk)
        form = EditFamilyEventForm(instance=event)
        form.fields['family'].initial = event.family.id

    return render(
        request,
        'genealogy/edit_family_event_modal.html',
        {
            'form': form, 
            'event': event,
            'event_type_text': str(event)
        }
    )

# person/<int:pk>/images
@login_required
def view_images(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    images = Image.objects.filter(id__in=ImagePerson.objects.filter(person=this_person).values('image'))

    return render(request, 'genealogy/view_images.html', {'person': this_person, 'images': images})

# images/<int:image_pk>/view
@login_required
def view_image(request, pk):
    role = 'owner'
    try:
        this_image = Image.objects.get(pk=pk)
        if this_image.tree.user != request.user:
            role = 'viewer'
    except Image.DoesNotExist:
        raise Http404("Image does not exist.")
    
    has_liked = ImageLike.objects.filter(image=this_image, user=request.user).exists()
    likes = ImageLike.objects.filter(image=this_image).count()

    comment_form = ImageCommentAddForm()
    comments = ImageComment.objects.filter(image=this_image).order_by('-commented_at')

    return render(request, 'genealogy/view_image_modal.html', {'image': this_image, 'has_liked': has_liked, 'likes': likes, 'comments_form': comment_form, 'comments': comments, 'role': role})

# person/<int:pk>/images/add
@login_required
@transaction.atomic
def add_image(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")
    
    if request.method == 'POST':
        form = ImageAddForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.tree = this_person.tree
            image.user = request.user
            image.save()
            mapping = ImagePerson()
            mapping.person = this_person
            mapping.image = image
            mapping.save()
            if not this_person.profile_image:
                this_person.profile_image = image
                this_person.save()
            messages.success(request, "Image uploaded successfully!")
            return render(request, 'genealogy/add_images.html', {'person': this_person, 'form': form})
        else:
            messages.error(request, "There was a problem uploading the image. Did you select one?")
            return render(request, 'genealogy/add_images.html', {'person': this_person, 'form': form})
    else:
        form = ImageAddForm()

    return render(request, 'genealogy/add_images.html', {'person': this_person, 'form': form})

# person/<int:person_pk>/images/<int:image_pk>/edit
@login_required
@transaction.atomic
def edit_image(request, person_pk, image_pk):
    this_person = get_object_or_404(Person, pk=person_pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    this_image = get_object_or_404(Image, pk=image_pk)
    if this_image.tree.user != request.user:
        raise Http404("Image not found for this user.")

    if request.method == 'POST':
        form = ImageEditForm(request.POST, instance=this_image)
        if form.is_valid():
            form.save()
            messages.success(request, "Image updated successfully!")
        else:
            messages.error(request, "There was a problem updating the image!")
        return render(request, 'genealogy/edit_image.html', {'person': this_person, 'image': this_image, 'form': form})
    else:  
        form = ImageEditForm(instance=this_image)

    return render(request, 'genealogy/edit_image.html', {'person': this_person, 'image': this_image, 'form': form})

# person/<int:person_pk>/images/<int:image_pk>/delete
@login_required
@transaction.atomic
def delete_image(request, person_pk, image_pk):
    this_person = get_object_or_404(Person, pk=person_pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    this_image = get_object_or_404(Image, pk=image_pk)
    if this_image.tree.user != request.user:
        raise Http404("Image not found for this user.")
    
    this_image.delete()
    messages.success(request, "Image successfully deleted!")

    return redirect('genealogy:view_images', pk=this_person.id)

# images/<int:image_pk>/like
@login_required
@transaction.atomic
def like_image(request, pk):
    role = 'owner'

    this_image = get_object_or_404(Image, pk=pk)
    if this_image.tree.user != request.user:
        role = 'viewer'
    
    if ImageLike.objects.filter(image=this_image, user=request.user).exists():
        ImageLike.objects.filter(image=this_image, user=request.user).delete()
        has_liked = False
    else:
        like = ImageLike()
        like.image = this_image
        like.user = request.user
        like.save()
        has_liked = True

    likes = ImageLike.objects.filter(image=this_image).count()

    return render(request, 'genealogy/image_like_section.html', {'image': this_image, 'has_liked': has_liked, 'likes': likes})

# images/<int:image_pk>/comments/add
@login_required
@transaction.atomic
def image_add_comment(request, pk):
    role = 'owner'

    this_image = get_object_or_404(Image, pk=pk)
    if this_image.tree.user != request.user:
        role = 'viewer'
    
    if request.method == 'POST':
        form = ImageCommentAddForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            comment = ImageComment()
            comment.image = this_image
            comment.user = request.user
            comment.comment = cd['comment']
            comment.save()

            comments = ImageComment.objects.filter(image=this_image).order_by('-commented_at')
            return render(request, 'genealogy/image_comments_section.html', {'image': this_image, 'comments_form': ImageCommentAddForm(), 'comments': comments})
        else:
            response = JsonResponse({'errors': dict(form.errors)}, status=400)
            return response

# images/<int:image_pk>/comments/<int:comment_pk>/delete
@login_required
@transaction.atomic
def image_delete_comment(request, image_pk, comment_pk):
    role = 'owner'

    this_image = get_object_or_404(Image, pk=image_pk)
    if this_image.tree.user != request.user:
        role = 'viewer'
    
    this_comment = get_object_or_404(ImageComment, pk=comment_pk)

    this_comment.delete()

    comments = ImageComment.objects.filter(image=this_image).order_by('-commented_at')

    return render(request, 'genealogy/image_comments_section.html', {'image': this_image, 'comments_form': ImageCommentAddForm(), 'comments': comments, 'role': role})

# person/<int:pk>/images/change-profile-photo
@login_required
@transaction.atomic
def change_profile_photo(request, pk):
    this_person = get_object_or_404(Person, pk=pk)
    if this_person.tree.user != request.user:
        raise Http404("Person not found in any of your trees.")

    images = Image.objects.filter(id__in=ImagePerson.objects.filter(person=this_person).values('image'))
    profile_photo = this_person.profile_image

    if request.method == "POST":
        image_id = request.POST.get('photo_id')
        selected_image = Image.objects.get(pk=int(image_id))

        if this_person.profile_image != selected_image:
            this_person.profile_image = selected_image
            this_person.save()

            messages.success(request, "Profile photo successfully updated!")

        return redirect('genealogy:person', pk=this_person.id)

    return render(request, 'genealogy/select_profile_photo_modal.html', {'person': this_person, 'images': images, 'profile_photo': profile_photo})

# tree/<int:pk>/add-person
@login_required
@transaction.atomic
def add_person(request, pk):
    this_tree = get_object_or_404(Tree, pk=pk)
    if this_tree.user != request.user:
        raise Http404("Tree not found for this user.")

    if request.method == 'POST':
        person_form = PersonNamesForm(request.POST)
        birth_form = EventShortForm(request.POST, prefix='birth')
        death_form = EventShortForm(request.POST, prefix='death')

        if not person_form.is_valid():
            response = JsonResponse({'errors': dict(person_form.errors)}, status=400)
            return response
        if not birth_form.is_valid():
            response = JsonResponse({'errors': dict(birth_form.errors)}, status=400)
            return response
        if not death_form.is_valid():
            response = JsonResponse({'errors': dict(death_form.errors)}, status=400)
            return response
        
        cd = person_form.cleaned_data
        if cd['first_name'] or cd['last_name']:
            new_person = Person()
            new_person.tree = this_tree
            new_person.first_name = cd['first_name']
            new_person.last_name = cd['last_name']
            new_person.sex = cd['sex']
            new_person.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(person=new_person, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(person=new_person, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            messages.success(request, 'New person added successfully!')

            return HttpResponse(status=204)
    else:
        person_form = PersonNamesForm()
        birth_form = EventShortForm(prefix='birth')
        death_form = EventShortForm(prefix='death')

    return render(
        request,
        'genealogy/add_new_person_modal.html', 
        {
            'person_form' : person_form,
            'birth_form': birth_form,
            'death_form': death_form
        }
    )

def get_single_parent_children(person):
    families = Family.objects.filter((Q(husband=person) & Q(wife=None)) | (Q(wife=person) & Q(husband=None)))

    if families:
        children = [(child.id, child.person) for child in Child.objects.filter(family=families[0])]
        return children
    else:
        return None
    
def find_close_relative(person):
    families = Family.objects.filter(Q(husband=person) | Q(wife=person))
    if families:
        for family in families:
            if family.husband == person and family.wife:
                return family.wife
            elif family.wife == person and family.husband:
                return family.husband
    father = person.get_father()
    if father:
        return father
    
    mother = person.get_mother()
    if mother:
        return mother

    if families:            
        for family in families:
            children = Child.objects.filter(family=family)
            for child in children:
                return child.person
            
    random_person = Person.objects.filter(tree=person.tree).exclude(id=person.id).first()
    
    return random_person
    
            
    