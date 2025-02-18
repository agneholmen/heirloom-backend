from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from .common import *
from ..forms import EditTreeForm, NewTreeForm, SearchForm
from .. import gedcom
from ..models import Child, Event, Family, FamilyEvent, Individual, Tree

from functools import reduce

import datetime
import json

EVENT_MAPPING = {
    'residence': 'RESI',
    'emigration': 'EMIG',
    'baptism': 'BAPM',
    'funeral': 'BURI',
    'immigration': 'IMMI',
    'graduation': 'GRAD',
    'cremation': 'CREM',
    'confirmation': 'CONF',
    'birth': 'BIRT',
    'death': 'DEAT',
}

FAMILY_EVENT_MAPPING = {
    'marriage': 'MARR',
    'divorce': 'DIV',
    'banns': 'MARB',
    'engagement': 'ENGA',
}

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

# tree/
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

# tree/<int:id>/view/<int:person_id>
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
        'image': get_default_image(first_person.sex) if not first_person.profile_image else get_profile_photo(first_person),
        'years': first_person.get_years(),
        'person_url': reverse('person', kwargs={'id': first_person.id}),
        'tree_url': reverse('view_tree', kwargs={'id': id, 'person_id': first_person.id}),
        'edit_url': reverse('edit_person', kwargs={'id': first_person.id})
    }

    people_data['parents'] = tree_get_parents(first_person, 1, generations, id)

    family = Family.objects.filter(Q(husband=first_person) | Q(wife=first_person))
    if family:
        if family[0].husband == first_person and family[0].wife:
            people_data['partner'] = get_person_tree_data(family[0].wife)
        elif family[0].wife == first_person and family[0].husband:
            people_data['partner'] = get_person_tree_data(family[0].husband)

        children = Child.objects.filter(family=family[0])
        if children:
            people_data['children'] = []
            for child in children:
                people_data['children'].append(get_person_tree_data(child.indi))

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

def get_person_tree_data(person):
    return {
        'first_name': person.first_name,
        'last_name': person.last_name,
        'id': person.id,
        'image': get_default_image(person.sex) if not person.profile_image else get_profile_photo(person),
        'years': person.get_years(),
        'person_url': reverse('person', kwargs={'id': person.id}),
        'tree_url': reverse('view_tree', kwargs={'id': person.tree.id, 'person_id': person.id}),
        'edit_url': reverse('edit_person', kwargs={'id': person.id})
    }

# tree/<int:id>/delete
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
        messages.success(request, 'Tree deleted successfully!')
        return redirect('family_tree')
    else:
        return render(request, 'genealogy/delete_tree_modal.html', {'tree': this_tree})

# tree/<int:id>/edit
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

# tree/<int:id>/download
@login_required
def download_tree(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")

    content = f'''0 HEAD
1 SUBM @SUBM1@
1 SOUR Project Heirloom
2 _TREE {this_tree.name}
1 DATE {datetime.datetime.now().strftime("%d %b %Y")}
2 TIME {datetime.datetime.now().strftime("%X")}
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @SUBM1@ SUBM
1 NAME Project Heirloom Member Trees Submitter
'''

    indi_id_counter = 1
    family_id_counter = 1

    family_instances = list(Family.objects.filter(tree=this_tree))
    for fam in family_instances:
        fam.family_id = f"@F{str(family_id_counter)}@"
        family_id_counter += 1
    Family.objects.bulk_update(family_instances, ["family_id"])

    individual_instances = list(Individual.objects.filter(tree=this_tree))
    for indi in individual_instances:
        indi.indi_id = f"@I{str(indi_id_counter)}@"
        indi_id_counter += 1

        content += f"0 {indi.indi_id} INDI\n"
        name = ""
        if indi.first_name:
            name += f"{indi.first_name} "
        if indi.last_name:
            name += f"/{indi.last_name}/"
        if name:
            content += f"1 NAME {name}\n"
            if indi.first_name:
                content += f"2 GIVN {indi.first_name}\n"
            if indi.last_name:
                content += f"2 SURN {indi.last_name}\n"
        
        content += f"1 SEX {indi.sex}\n"
        try:
            child = Child.objects.get(indi=indi)
            content += f"1 FAMC {child.family.family_id}\n"
        except:
            pass

        indi_families = Family.objects.filter(Q(husband=indi) or Q(wife=indi))
        for fam in indi_families:
            content += f"1 FAMS {fam.family_id}\n"

        indi_events = Event.objects.filter(indi=indi)
        for event in indi_events:
            content += f"1 {EVENT_MAPPING[event.event_type]}\n"
            if event.date:
                content += f"2 DATE {event.date}\n"
            if event.place:
                content += f"2 PLAC {event.place}\n"
            if event.description:
                content += f"2 NOTE {event.description}\n"

    Individual.objects.bulk_update(individual_instances, ["indi_id"])

    for fam in family_instances:
        content += f"0 {fam.family_id} FAM\n"
        if fam.husband:
            content += f"1 HUSB {fam.husband.indi_id}\n"
        if fam.wife:
            content += f"1 WIFE {fam.wife.indi_id}\n"

        children = Child.objects.filter(family=fam)
        for child in children:
            content += f"1 CHIL {child.indi.indi_id}\n"

        family_events = FamilyEvent.objects.filter(family=fam)
        for event in family_events:
            content += f"1 {FAMILY_EVENT_MAPPING[event.event_type]}\n"
            if event.date:
                content += f"2 DATE {event.date}\n"
            if event.place:
                content += f"2 PLAC {event.place}\n"
            if event.description:
                content += f"2 NOTE {event.description}\n"

    response = HttpResponse(content, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="{this_tree.name}.ged"'

    return response

# tree/get-list
@login_required
def get_tree_list(request):
    trees = Tree.objects.filter(user=request.user)
    trees = trees.annotate(number_of_individuals=Count("individuals"))

    return render(request, 'genealogy/tree_list.html', {'trees': trees})


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
            'image': get_default_image(father.sex) if not father.profile_image else get_profile_photo(father),
            'years': father.get_years(),
            'person_url': reverse('person', kwargs={'id': father.id}),
            'tree_url': reverse('view_tree', kwargs={'id': tree_id, 'person_id': father.id}),
            'edit_url': reverse('edit_person', kwargs={'id': father.id}),
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
            'image': get_default_image(mother.sex) if not mother.profile_image else get_profile_photo(mother),
            'years': mother.get_years(),
            'person_url': reverse('person', kwargs={'id': mother.id}),
            'tree_url': reverse('view_tree', kwargs={'id': tree_id, 'person_id': mother.id}),
            'edit_url': reverse('edit_person', kwargs={'id': mother.id}),
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

# search/
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
                query += f"&birth_year_end={cd['birth_year_end']}"
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

# search/update-result-row/<int:id>
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