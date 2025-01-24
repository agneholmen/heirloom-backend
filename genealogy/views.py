from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.urls import reverse
from .forms import (
    AddEventForm,
    AddExistingPersonChildForm,
    AddFamilyEventForm,
    EventShortForm,
    EditEventForm,
    EditTreeForm,
    EditFamilyEventForm,
    FindExistingPersonForm,
    LoginForm,
    NewTreeForm,
    PersonNamesFamilyForm,
    PersonNamesForm,
    ProfileEditForm,
    RemoveRelationshipForm,
    SearchForm,
    SelectEventForm,
    UserEditForm,
    UserRegistrationForm
)
from .models import (
    Child,
    Event,
    Family,
    FamilyEvent,
    Individual, 
    Profile, 
    Tree
)

from . import gedcom

from .date_functions import extract_year

from functools import reduce

from itertools import chain

import json

NAMES_REPLACE = [
    ["Annika", "Annicka"],
    ["Brita", "Britta"],
    ["Cajsa", "Kajsa", "Caisa"],
    ["Carl", "Karl"],
    ["Catharina", "Katharina", "Katarina"],
    ["Christina", "Kristina"],
    ["Elisabet", "Elisabeth"],
    ["Erik", "Eric"],
    ["Fredrik", "Fredric"],
    ["Gustaf", "Gustav"],
    ["Halvar", "Halvard"],
    ["Kerstin", "Kjerstin"],
    ["Maja", "Maria"],
    ["Olof", "Olov"],
    ["Oscar", "Oskar"],
    ["Per", "Pär", "Pehr", "Pähr"],
    ["Sofia", "Sophia"],
    ["Ulrika", "Ulrica"],
]

SURNAMES_REPLACE = [
    ["Eriksson", "Ersson"],
    ["Eriksdotter", "Ersdotter"],
    ["Olofsson", "Olsson"],
    ["Olofsdotter", "Olsdotter"],
]

@login_required
def home(request):
    return render(
        request,
        'genealogy/home.html',
        {'section': 'home'}
    )

@login_required
def family_tree(request):
    if request.method == "POST":
        form = NewTreeForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            if Tree.objects.filter(Q(name=cd['name']) & Q(user=request.user)).count() > 0:
                messages.error(request, 'A tree with that name already exists!')
            else:
                new_tree = Tree(user=request.user)
                if request.FILES:
                    new_tree.gedcom_file = request.FILES["file"]

                new_tree.name = cd['name']
                new_tree.description = cd['description']
                new_tree.save()

                # If a GEDCOM file was uploaded, add all Individual, Family, and Child to DB
                if new_tree.gedcom_file:
                    gedcom.handle_uploaded_file(new_tree)

                messages.success(request, 'New tree added successfully!')

                # We don't want to save the properties in the form if new tree is added
                form = NewTreeForm()

    else:
        form = NewTreeForm()

    trees = Tree.objects.filter(user=request.user).order_by("name")
    trees = trees.annotate(number_of_individuals=Count("individuals"))

    return render(
        request,
        'genealogy/family_tree.html',
        {
            'section': 'family_tree',
            'upload_form': form,
            'trees': trees
        }
    )

@login_required
def images(request):
    return render(
        request,
        'genealogy/images.html',
        {'section': 'images'}
    )

@login_required
def search(request):
    trees = Tree.objects.filter(user=request.user).order_by('name')

    if request.method == 'GET' and request.GET:
        query = ''
        search_form = SearchForm(request.GET)
        search_form.fields["tree"].queryset = trees
        if search_form.is_valid():
            cd = search_form.cleaned_data
            
            and_conditions = []
            or_conditions = []
            name_conditions = []
            birth_conditions = []
            death_conditions = []

            query += f"&tree={cd['tree'].id}"
            query += f"&results_per_page={cd['results_per_page']}"
            if cd['name']:
                query += f"&name={cd['name']}"
                name_strings = cd['name'].split()
                for name in name_strings:
                    name_or_conditions = []
                    found_first = False
                    found_last = False
                    for n in NAMES_REPLACE:
                        if name in n:
                            for variation in n:
                                name_or_conditions.append(Q(first_name__icontains=variation))
                                # Only search first name for variations of the same name
                                if variation == name:
                                    name_or_conditions.append(Q(last_name__icontains=variation))
                                found_first = True
                            if found_first:
                                break
                    if found_first == False:
                        for n in SURNAMES_REPLACE:
                            if name in n:
                                for variation in n:
                                    name_or_conditions.append(Q(last_name__icontains=variation))
                                    # Only search first name for variations of the same name
                                    if variation == name:
                                        name_or_conditions.append(Q(first_name__icontains=variation))
                                    found_last = True
                                if found_last:
                                    break
                        if found_last == False:
                            name_or_conditions.append(Q(first_name__icontains=name))
                            name_or_conditions.append(Q(last_name__icontains=name))

                    name_or_conditions = reduce(lambda x, y: x | y, name_or_conditions)
                    if name_conditions:
                        name_conditions = name_conditions & name_or_conditions
                    else:
                        name_conditions = name_or_conditions

            birth_conditions = []
            death_conditions = []

            if cd['birth_place']:
                query += f"&birth_place={cd['birth_place']}"
                birth_conditions.append(Q(event__place__icontains=cd['birth_place']))
            if cd['birth_date']:
                query += f"&birth_date={cd['birth_date']}"
                birth_conditions.append(Q(event__date__icontains=cd['birth_date']))
            if cd['birth_year_start']:
                query += f"&birth_year_start={cd['birth_year_start']}"
                birth_conditions.append(Q(event__year__gte=cd['birth_year_start']))
            if cd['birth_year_end']:
                query += f"&birth_year_end{cd['birth_year_end']}"
                birth_conditions.append(Q(event__year__lte=cd['birth_year_end']))
            if cd['death_place']:
                query += f"&death_place={cd['death_place']}"
                death_conditions.append(Q(event__place__icontains=cd['death_place']))
            if cd['death_date']:
                query += f"&death_date={cd['death_date']}"
                death_conditions.append(Q(event__date__icontains=cd['death_date']))
            if cd['death_year_start']:
                query += f"&death_year_start={cd['death_year_start']}"
                death_conditions.append(Q(event__year__gte=cd['death_year_start']))
            if cd['death_year_end']:
                query += f"&death_year_end={cd['death_year_end']}"
                death_conditions.append(Q(event__year__lte=cd['death_year_end']))

            final_query = Q(tree=cd['tree'])
            if and_conditions:
                combined_and_conditions = reduce(lambda x, y: x & y, and_conditions)
                final_query = final_query & combined_and_conditions
            if or_conditions:
                combined_or_conditions = reduce(lambda x, y: x | y, or_conditions)
                final_query = final_query & combined_or_conditions
            if name_conditions:
                final_query = final_query & name_conditions

            results_per_page = cd['results_per_page']
            people = Individual.objects.filter(final_query)
            if birth_conditions:
                birth_query = Q(event__event_type='birth') & reduce(lambda x, y: x & y, birth_conditions)
                people = people.filter(birth_query)
            if death_conditions:
                death_query = Q(event__event_type='death') & reduce(lambda x, y: x & y, death_conditions)
                people = people.filter(death_query)
            paginator = Paginator(people, results_per_page)
            page_number = request.GET.get('page', 1)
            try:
                people = paginator.page(page_number)
            except EmptyPage:
                people = paginator.page(paginator.num_pages)

            return render(
                request,
                'genealogy/search.html',
                {
                    'section': 'search',
                    'trees': trees,
                    'search_form': search_form,
                    'people': people,
                    'search_query': query
                }
            )
            
    else:
        search_form = SearchForm()
        search_form.fields["tree"].queryset = trees

    return render(
        request,
        'genealogy/search.html',
        {
            'section': 'search',
            'trees': trees,
            'search_form': search_form
        }
    )

@login_required
def person(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")

    birth = this_person.get_birth_event()
    death = this_person.get_death_event()

    father = this_person.get_father()
    mother = this_person.get_mother()
    siblings = None
    half_siblings = None
    families = None
    children_objects = Child.objects.filter(indi=this_person)
    if children_objects:
        siblings = Child.objects.filter(family=children_objects[0].family).exclude(id=children_objects[0].id)

        half_sibling_queries = Q()
        if father is not None:
            half_sibling_queries |= Q(husband=father) & ~Q(wife=mother)
        if mother is not None:
            half_sibling_queries |= Q(wife=mother) & ~Q(husband=father)

        half_sibling_families = Family.objects.filter(half_sibling_queries)
        half_siblings = Child.objects.filter(family__in=half_sibling_families).exclude(indi=this_person)
    
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
            family['children'] = Child.objects.filter(family=f)
            # Add timeline events for children
            for child in family['children']:
                c_birth = child.indi.get_birth_event()
                c_death = child.indi.get_death_event()
                if c_birth and c_birth.year:
                    timeline_events.append(
                        {
                            'year': c_birth.year, 
                            'description': "", 
                            'date': c_birth.date,
                            'event_type': 'birth', 
                            'event_type_full': f"Birth of {'son' if child.indi.sex == 'M' else 'daughter' if child.indi.sex == 'F' else 'child'}",
                            'place': c_birth.place, 
                            'id': child.indi.id,
                            'model_type': 'relative',
                            'family_member': child.indi,
                            'years_since_birth': c_birth.year - birth.year
                        }
                    )
                if c_death and death and c_death.year < death.year:
                    timeline_events.append(
                        {
                            'year': c_death.year, 
                            'description': "", 
                            'date': c_death.date,
                            'event_type': 'birth', 
                            'event_type_full': f"Death of {'son' if child.indi.sex == 'M' else 'daughter' if child.indi.sex == 'F' else 'child'}",
                            'place': c_death.place, 
                            'id': child.indi.id,
                            'model_type': 'relative',
                            'family_member': child.indi,
                            'years_since_birth': c_death.year - birth.year
                        }
                    )

            if f.husband == this_person and f.wife:
                family['partner'] = f.wife
            if f.wife == this_person and f.husband:
                family['partner'] = f.husband
            
            # Add timeline events for partner
            if family['partner']:
                p_death = family['partner'].get_death_event()
                if p_death and death and p_death.year < death.year:
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
                            'family_member': family['partner'],
                            'years_since_birth': p_death.year - birth.year
                        }
                    )

            families.append(family)

    events = Event.objects.filter(indi=this_person).order_by('year')
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
                    'model_type': 'basic',
                    'years_since_birth': e.year - birth.year if birth else None
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
                'model_type': 'family',
                'years_since_birth': birth.year if birth else None
            }
        if new_event['year']:
            timeline_events.append(new_event)
        else:
            timeline_events_no_year.append(new_event)

    # Add events related to relatives
    for s in chain(siblings or [], half_siblings or []):
        s_birth = s.indi.get_birth_event()
        s_death = s.indi.get_death_event()
        if s_birth and birth and s_birth.year > birth.year and not (death and s_birth.year > death.year):
            timeline_events.append(
                {
                    'year': s_birth.year, 
                    'description': "", 
                    'date': s_birth.date,
                    'event_type': 'birth', 
                    'event_type_full': f"Birth of {'brother' if s.indi.sex == 'M' else 'sister' if s.indi.sex == 'F' else 'sibling'}",
                    'place': s_birth.place, 
                    'id': s.indi.id,
                    'model_type': 'relative',
                    'family_member': s.indi,
                    'years_since_birth': s_birth.year - birth.year
                }
            )
        if s_death and death and s_death.year < death.year and not (birth and s_death.year < birth.year):
            timeline_events.append(
                {
                    'year': s_death.year, 
                    'description': "", 
                    'date': s_death.date,
                    'event_type': 'death', 
                    'event_type_full': f"Death of {'brother' if s.indi.sex == 'M' else 'sister' if s.indi.sex == 'F' else 'sibling'}",
                    'place': s_death.place,
                    'id': s.indi.id,
                    'model_type': 'relative',
                    'family_member': s.indi,
                    'years_since_birth': s_death.year - birth.year
                }
            )

    if father:
        f_death = father.get_death_event()
        if not (f_death and death and f_death.year > death.year) and f_death and f_death.year:
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
                    'family_member': father,
                    'years_since_birth': f_death.year - birth.year
                }
            )
    if mother:
        m_death = mother.get_death_event()
        if not (m_death and death and m_death.year > death.year) and m_death and m_death.year:
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
                    'family_member': mother,
                    'years_since_birth': m_death.year - birth.year
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
                                'model_type': 'basic', 
                                'years_since_birth': 0
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
                'model_type': 'basic',
                'years_since_birth': death.year - birth.year if birth else None
            }
        )

    timeline_events.extend(timeline_events_no_year)

    # More should be added
    for event in timeline_events:
        if event['event_type'] == 'birth':
            event['icon'] = '🎂'
        elif event['event_type'] == 'death':
            event['icon'] = '☠️'
        elif event['event_type'] == 'marriage':
            event['icon'] = '💍'
        elif event['event_type'] == 'residence':
            event['icon'] = '🏠'
        else:
            event['icon'] = '📆'

    return render(
        request,
        'genealogy/person.html',
        {
            'section': 'search',
            'person': this_person,
            'person_image': get_default_image(this_person.sex),
            'birth': birth,
            'death': death,
            'father': father,
            'mother': mother,
            'siblings': siblings,
            'half_siblings': half_siblings,
            'families': families,
            'events': timeline_events
        }
    )

@login_required
def edit_person(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
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
        response.headers = {'HX-Trigger': f'update-person-{str(id)}'}
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

@login_required
def edit_relationships(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
    if request.method == 'POST':
        used_form = RemoveRelationshipForm(request.POST)

        if used_form.is_valid():
            cd = used_form.cleaned_data
            if cd['relationship_type'] == 'father':
                this_child = Child.objects.get(indi=this_person, family__husband=cd['related_person_id'])
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
                this_child = Child.objects.get(indi=this_person, family__wife=cd['related_person_id'])
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
                this_child = Child.objects.get(Q(indi=cd['related_person_id']) & (Q(family__husband=this_person) | Q(family__wife=this_person)))
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
        children_objects = Child.objects.filter(indi=this_person)
        if children_objects:
            if father:
                father_form = RemoveRelationshipForm(initial={'relationship_type': 'father', 'related_person_id': father.id})
            if mother:
                mother_form = RemoveRelationshipForm(initial={'relationship_type': 'mother', 'related_person_id': mother.id})

        children = Child.objects.filter(Q(family__husband=this_person) | Q(family__wife=this_person))
        for c in children:
            child_form = RemoveRelationshipForm(initial={'relationship_type': 'child', 'related_person_id': c.indi.id})
            children_forms.append((c.indi, child_form))
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

@login_required
def delete_person(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
    if request.method == "POST":
        try:
            this_person.delete()
            messages.success(
                request,
                "Person successfully removed!"
            )
            return HttpResponse(status=204)
        except:
            messages.error(request, "There was a problem removing the person!")
            return HttpResponse(status=400)
    else:
        return render(request, 'genealogy/delete_person_modal.html', {'person': this_person})

@login_required
def add_person_as_partner(request, id, family_id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
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

            partner = Individual()
            partner.tree = this_person.tree
            partner.first_name = cd['first_name']
            partner.last_name = cd['last_name']
            partner.sex = cd['sex']
            partner.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(indi=partner, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(indi=partner, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            try:
                family = Family.objects.get(id=family_id)
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

            return HttpResponse(status=204)
            
        elif request.POST.get('identifier') == 'add_existing_person':
            find_people_form = FindExistingPersonForm(request.POST, tree_id=this_person.tree.id)
            dropdown_persons = get_dropdown_persons(request.POST.get('person'), this_person.tree.id)
            for p in dropdown_persons:
                find_people_form.fields['selected_person'].choices.append((p.id, p.get_name_years()))

            if find_people_form.is_valid():
                cd = find_people_form.cleaned_data
                if cd['selected_person'].isnumeric() == False:
                    errors = {'no_partner_selected': 'You did not select a partner!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                try:
                    partner = Individual.objects.get(id=cd['selected_person'])
                except Individual.DoesNotExist:
                    raise Http404("Individual does not exist.")
                
                if Family.objects.filter((Q(wife=this_person) & Q(husband=partner)) | (Q(wife=partner) & Q(husband=this_person))).exists():
                    errors = {'already_a_family': 'The selected people already have a family!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                if (this_person.get_birth_year() and partner.get_death_year() and this_person.get_birth_year() > partner.get_death_year()) \
                    or (this_person.get_death_year() and partner.get_birth_year() and partner.get_birth_year() > this_person.get_death_year()):
                    errors = {'not_alive_at_the_same_time': 'The selected people were not alive at the same time!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                
                family = Family()
                if this_person.sex == 'M':
                    family.husband = this_person
                    family.wife = partner
                else:
                    family.husband = partner
                    family.wife = this_person
                family.tree = this_person.tree
                family.save()

                return HttpResponse(status=204)
            else:
                response = JsonResponse({'errors': dict(find_people_form.errors)}, status=400)
                return response

    else:
        person_form = PersonNamesForm()
        person_form.fields['identifier'].initial = 'add_new_person'
        birth_form = EventShortForm(prefix='birth')
        death_form = EventShortForm(prefix='death')
        find_people_form = FindExistingPersonForm(tree_id=this_person.tree.id)

    title = f'Add Partner for {this_person}'

    return render(
        request, 
        'genealogy/add_new_existing_person_modal.html', 
        {
            'person_form': person_form,
            'birth_form': birth_form,
            'death_form': death_form,
            'search_form': find_people_form, 
            'modal_title': title
        }
    )

@login_required
def search_people_for_dropdown(request, id):
    query = request.POST.get('person', '')
    persons = get_dropdown_persons(query, id)

    return render(request, 'genealogy/person_dropdown.html', {'persons': persons})

@login_required
def families_for_dropdown(request):
    person = request.POST.get('selected_person', '')
    families = get_families(person)

    return render(request, 'genealogy/family_dropdown.html', {'families': families})

def get_families(person):
    try:
        this_person = Individual.objects.get(id=person)
        families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person))
        family_choices = [(family.id, family) for family in families]
        if not Family.objects.filter((Q(husband=this_person) & Q(wife=None)) | (Q(wife=this_person) & Q(husband=None))).exists():
            family_choices.append((0, f'{this_person} and unknown partner'))
    except:
        family_choices = []

    return family_choices

def get_dropdown_persons(query, id):
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
        tree = Tree.objects.get(id=id)
        persons = Individual.objects.filter(reduce(lambda x, y: x & y, db_query_items) & Q(tree=tree))
        # If two years included, also search for specific death year
        if len(years) == 2:
            persons = persons.filter(death_query)
        
        # Get first 10 results
        persons = persons[:10]

    else:
        persons = Individual.objects.none()

    return persons

@login_required
def add_person_as_child(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
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
            child = Individual()
            child.tree = this_person.tree
            child.first_name = cd['first_name']
            child.last_name = cd['last_name']
            child.sex = cd['sex']
            child.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(indi=child, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(indi=child, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            new_child = Child()
            new_child.indi = child
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
                    child = Individual.objects.get(id=cd['selected_person'])
                except Individual.DoesNotExist:
                    raise Http404("Individual does not exist.")
                
                if Child.objects.filter(indi=child).exists():
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
                new_child.indi = child
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

@login_required
def add_person_as_parent(request, id, parent):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")

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

            new_parent = Individual()
            new_parent.tree = this_person.tree
            new_parent.first_name = cd['first_name']
            new_parent.last_name = cd['last_name']
            new_parent.sex = cd['sex']
            new_parent.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(indi=new_parent, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(indi=new_parent, event_type='death', date=df_data['date'], place=df_data['place'])
                death_event.save()

            # Basically, already has a parent
            try:
                child = Child.objects.get(indi=this_person)
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
                new_child.indi = this_person
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
                    new_parent = Individual.objects.get(id=cd['selected_person'])
                except Individual.DoesNotExist:
                    raise Http404("Individual does not exist.")
                
                # Find existing family. If failure, create new family.
                try:
                    child = Child.objects.get(indi=this_person)
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
                    new_child.indi = this_person
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

@login_required
def add_person(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")

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
            new_person = Individual()
            new_person.tree = this_tree
            new_person.first_name = cd['first_name']
            new_person.last_name = cd['last_name']
            new_person.sex = cd['sex']
            new_person.save()

            bf_data = birth_form.cleaned_data
            if bf_data['date'] or bf_data['place']:
                birth_event = Event(indi=new_person, event_type='birth', date=bf_data['date'], place=bf_data['place'])
                birth_event.save()

            df_data = death_form.cleaned_data
            if df_data['date'] or df_data['place']:
                death_event = Event(indi=new_person, event_type='death', date=df_data['date'], place=df_data['place'])
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

@login_required
def delete_tree(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")
    
    if request.method == "POST":
        this_tree.delete()
        if request.headers.get('HX-Request') == 'true':
            return HttpResponse(status=204, headers={'HX-Trigger': 'tree-list-changed'})
        return redirect('family_tree')
    else:
        return render(request, 'genealogy/delete_tree_modal.html', {'tree': this_tree})

@login_required
def edit_tree(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")

    if request.method == 'POST':
        form = EditTreeForm(request.POST, instance=this_tree)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=204, headers={'HX-Trigger': 'tree-list-changed'})
            return response
        else:
            response = JsonResponse({'errors': dict(form.errors)}, status=400)
            return response
    else:
        form = EditTreeForm(instance=this_tree)

    return render(
        request, 
        'genealogy/edit_tree_modal.html',
        {'tree': this_tree, 'form': form}
    )

@login_required
def event_list(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")

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

@login_required
def add_event(request, id, event_type):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
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
                event.indi = this_person
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

@login_required
def edit_event(request, id):
    if request.method == 'POST':
        event = Event.objects.get(id=id)
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
        event = Event.objects.get(id=id)
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

@login_required
def edit_family_event(request, id):
    if request.method == 'POST':
        event = FamilyEvent.objects.get(id=id)
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
        event = FamilyEvent.objects.get(id=id)
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

@login_required
def get_tree_list(request):
    trees = Tree.objects.filter(user=request.user)
    trees = trees.annotate(number_of_individuals=Count("individuals"))

    return render(request, 'genealogy/tree_list.html', {'trees': trees})

@login_required
def view_tree(request, id, person_id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")
    
    this_tree.number_of_individuals = Tree.objects.filter(id=id).annotate(number_of_individuals=Count("individuals")).values_list("number_of_individuals", flat=True).first()
    if this_tree.number_of_individuals == 0:
        return render(
            request, 
            'genealogy/view_tree.html', 
            {
                'section': 'family_tree', 
                'tree': this_tree
            }
        )
    
    if person_id == 0:
        most_recent_person = Individual.objects.filter(tree=this_tree).order_by('id').first()
        return redirect('view_tree', id=id, person_id=most_recent_person.id)

    try:
        first_person = Individual.objects.get(id=person_id)
        if first_person.tree != this_tree:
            raise Http404("Individual not found in this tree.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")

    generations = 3

    people_data = {
        'first_name': first_person.first_name,
        'last_name': first_person.last_name,
        'id': first_person.id,
        'image': get_default_image(first_person.sex),
        'years': first_person.get_years(),
        'person_url': reverse('person', kwargs={'id': first_person.id})
    }

    people_data['parents'] = tree_get_parents(first_person, 1, generations, id)

    return render(
        request, 
        'genealogy/view_tree.html', 
        {
            'section': 'family_tree', 
            'tree': this_tree, 
            'first_person': first_person, 
            'people': json.dumps(people_data)
        }
    )

def tree_get_parents(current_person, generation, max_generation, tree_id):
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
            'image': get_default_image(father.sex),
            'years': father.get_years(),
            'person_url': reverse('view_tree', kwargs={'id': tree_id, 'person_id': father.id}),
            'parent_type': 'father',
            'parents': tree_get_parents(father, generation + 1, max_generation, tree_id)
        })
    else:
        parents.append({
            'id': 0,
            'child_id': current_person.id,
            'person_url': reverse('add_person_as_parent', kwargs={'id': current_person.id, 'parent': 'father'}),
            'parent_type': 'father',
            'parents': []
        })
    if mother:
        parents.append({
            'first_name': mother.first_name,
            'last_name': mother.last_name,
            'id': mother.id,
            'image': get_default_image(mother.sex),
            'years': mother.get_years(),
            'person_url': reverse('view_tree', kwargs={'id': tree_id, 'person_id': mother.id}),
            'parent_type': 'mother',
            'parents': tree_get_parents(mother, generation + 1, max_generation, tree_id)
        })
    else:
        parents.append({
            'id': 0,
            'child_id': current_person.id,
            'person_url': reverse('add_person_as_parent', kwargs={'id': current_person.id, 'parent': 'mother'}),
            'parent_type': 'mother',
            'parents': []
        })

    return parents

def get_default_image(sex):
    if sex == 'M':
        return static('images/male.png')
    elif sex == 'F':
        return static('images/female.png')
    else:
        return static('images/unknown.png')

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd['username'],
                password=cd['password']
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'genealogy/login.html', {'form': form})

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            # Set the chosen password
            new_user.set_password(
                user_form.cleaned_data['password']
            )
            # Save the User object
            new_user.save()
            Profile.objects.create(user=new_user)
            return render(
                request,
                'genealogy/register_done.html',
                {'new_user': new_user}
            )
    else:
        user_form = UserRegistrationForm()
    return render(
        request,
        'genealogy/register.html',
        {'user_form': user_form}
    )

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserEditForm(
            instance=request.user,
            data=request.POST
        )
        profile_form = ProfileEditForm(
            instance=request.user.profile,
            data=request.POST,
            files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(
                request,
                'Profile updated successfully!'
            )
        else:
            messages.error(request, 'Error updating your profile!')

    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)

    return render(
        request,
        'genealogy/edit_profile.html',
        {
            'user_form': user_form,
            'profile_form': profile_form,
            'section': 'edit_profile'
        }
    )

@login_required
def update_search_result_row(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
    return render(
        request,
        'genealogy/search_result_row.html',
        {'person': this_person}
    )