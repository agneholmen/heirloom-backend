from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from .forms import (
    AddEventForm,
    AddExistingPersonChildForm,
    AddFamilyEventForm,
    AddPersonChildForm,
    AddPersonForm,
    EditPersonForm,
    EditTreeForm,
    FindExistingPersonForm,
    LoginForm,
    NewTreeForm,
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

NAMES_REPLACE = [
    ["Maja", "Maria"],
    ["Gustaf", "Gustav"],
    ["Carl", "Karl"],
    ["Brita", "Britta"],
    ["Kerstin", "Kjerstin"],
    ["Halvar", "Halvard"],
    ["Per", "Pär", "Pehr", "Pähr"],
    ["Kajsa", "Cajsa", "Caisa"],
    ["Kristina", "Christina"],
    ["Katharina", "Katarina", "Catharina"],
    ["Sofia", "Sophia"],
    ["Ulrika", "Ulrica"],
    ["Fredrik", "Fredric"],
    ["Erik", "Eric"]
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

            query += f"&tree={cd['tree'].id}"
            query += f"&results_per_page={cd['results_per_page']}"
            if cd['name']:
                query += f"&name={cd['name']}"
                name_strings = cd['name'].split()
                for name in name_strings:
                    name_or_conditions = []
                    found = False
                    for n in NAMES_REPLACE:
                        if name in n:
                            for variation in n:
                                name_or_conditions.append(Q(first_name__icontains=variation))
                                # Only search first name for variations of the same name
                                if variation == name:
                                    name_or_conditions.append(Q(last_name__icontains=variation))
                                found = True
                            if found:
                                break
                    if found == False:
                        name_or_conditions.append(Q(first_name__icontains=name))
                        name_or_conditions.append(Q(last_name__icontains=name))

                    name_or_conditions = reduce(lambda x, y: x | y, name_or_conditions)
                    if name_conditions:
                        name_conditions = name_conditions & name_or_conditions
                    else:
                        name_conditions = name_or_conditions

            if cd['birth_place']:
                query += f"&birth_place={cd['birth_place']}"
                and_conditions.append(Q(birth_place__icontains=cd['birth_place']))
            if cd['birth_date']:
                query += f"&birth_date={cd['birth_date']}"
                and_conditions.append(Q(birth_date__icontains=cd['birth_date']))
            if cd['birth_year_start']:
                query += f"&birth_year_start={cd['birth_year_start']}"
                and_conditions.append(Q(birth_year__gte=cd['birth_year_start']))
            if cd['birth_year_end']:
                query += f"&birth_year_end{cd['birth_year_end']}"
                and_conditions.append(Q(birth_year__lte=cd['birth_year_end']))
            if cd['death_place']:
                query += f"&death_place={cd['death_place']}"
                and_conditions.append(Q(death_place__icontains=cd['death_place']))
            if cd['death_date']:
                query += f"&death_date={cd['death_date']}"
                and_conditions.append(Q(death_date__icontains=cd['death_date']))
            if cd['death_year_start']:
                query += f"&death_year_start={cd['death_year_start']}"
                and_conditions.append(Q(death_year__gte=cd['death_year_start']))
            if cd['death_year_end']:
                query += f"&death_year_end={cd['death_year_end']}"
                and_conditions.append(Q(death_year__lte=cd['death_year_end']))

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

    father = None
    mother = None
    siblings = None
    half_siblings = None
    families = None
    children_objects = Child.objects.filter(indi=this_person)
    if children_objects:
        # Needs fixing later to handle if it belongs to multiple families. For now I'll just take the first item.
        father = children_objects[0].family.husband
        mother = children_objects[0].family.wife

        siblings = Child.objects.filter(family=children_objects[0].family).exclude(id=children_objects[0].id)

        half_sibling_queries = Q()
        if father is not None:
            half_sibling_queries |= Q(husband=father) & ~Q(wife=mother)
        if mother is not None:
            half_sibling_queries |= Q(wife=mother) & ~Q(husband=father)

        half_sibling_families = Family.objects.filter(half_sibling_queries)
        half_siblings = Child.objects.filter(family__in=half_sibling_families).exclude(indi=this_person)
    
    family_objects = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person))
    if family_objects:
        families = []
        for f in family_objects:
            family = {
                'partner': None, 
                'children': []
            }
            family['children'] = Child.objects.filter(family=f)
            if f.husband == this_person and f.wife:
                family['partner'] = f.wife
            if f.wife == this_person and f.husband:
                family['partner'] = f.husband

            families.append(family)
        
    return render(
        request,
        'genealogy/person.html',
        {
            'section': 'search',
            'person': this_person,
            'father': father,
            'mother': mother,
            'siblings': siblings,
            'half_siblings': half_siblings,
            'families': families
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
        form = EditPersonForm(request.POST, instance=this_person)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=204)
            response.headers = {'HX-Trigger': f'update-person-{str(id)}'}
            return response
        else:
            return render(
                request, 
                'genealogy/edit_person_modal.html',
                {'form': form},
                status=400
            )
    else:
        form = EditPersonForm(instance=this_person)

    return render(
        request, 
        'genealogy/edit_person_modal.html',
        {'form': form}
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
        father = None
        mother = None
        father_form = None
        mother_form = None
        children_forms = []
        partner_forms = []
        children_objects = Child.objects.filter(indi=this_person)
        if children_objects:
            # Needs fixing later to handle if it belongs to multiple families. For now I'll just take the first item.
            father = children_objects[0].family.husband
            mother = children_objects[0].family.wife

            if father:
                father_form = RemoveRelationshipForm(initial={'relationship_type': 'father', 'related_person_id': father.id})
            if mother:
                mother_form = RemoveRelationshipForm(initial={'relationship_type': 'mother', 'related_person_id': mother.id})

        children = Child.objects.filter(Q(family__husband=this_person) | Q(family__wife=this_person))
        for c in children:
            child_form = RemoveRelationshipForm(initial={'relationship_type': 'child', 'related_person_id': c.indi.id})
            children_forms.append((c.indi, child_form))
        families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person))
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
def add_person_as_partner(request, id):
    try:
        this_person = Individual.objects.get(id=id)
        if this_person.tree.user != request.user:
            raise Http404("Individual not found in any of your trees.")
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_new_person':
            form = AddPersonForm(request.POST)
            find_people_form = FindExistingPersonForm(tree_id=this_person.tree.id)
            if form.is_valid():
                cd = form.cleaned_data

                if cd['first_name'] or cd['last_name']:
                    partner = Individual()
                    partner.tree = this_person.tree
                    partner.first_name = cd['first_name']
                    partner.last_name = cd['last_name']
                    partner.birth_place = cd['birth_place']
                    partner.birth_date = cd['birth_date']
                    partner.death_place = cd['death_place']
                    partner.death_date = cd['death_date']
                    partner.sex = cd['sex']
                    partner.save()

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
                    errors = {'name': 'A person needs at least a first name or last name!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response   

            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
            
        elif request.POST.get('identifier') == 'add_existing_person':
            find_people_form = FindExistingPersonForm(request.POST, tree_id=this_person.tree.id)
            dropdown_persons = get_dropdown_persons(request.POST.get('person'), this_person.tree.id)
            for p in dropdown_persons:
                find_people_form.fields['selected_person'].choices.append((p.id, p.get_name_years()))
            form = AddPersonForm()

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
                
                if (this_person.birth_year and partner.death_year and this_person.birth_year > partner.death_year) \
                    or (this_person.death_year and partner.birth_year and partner.birth_year > this_person.death_year):
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
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response

    else:
        form = AddPersonForm()
        find_people_form = FindExistingPersonForm(tree_id=this_person.tree.id)

    title = f'Add Partner for {this_person}'

    return render(request, 'genealogy/add_new_existing_person_modal.html', {'form': form, 'search_form': find_people_form, 'modal_title': title})

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
        family_choices.append((0, f'{this_person} and unknown partner'))
    except:
        family_choices = []

    return family_choices

def get_dropdown_persons(query, id):
    if query:
        db_query_items = []
        query_items = query.split(" ")
        for q in query_items:
            if q.isnumeric():
                item = (Q(birth_year=q) | Q(death_year=q))
            else:
                item = (Q(first_name__icontains=q) | Q(last_name__icontains=q))
            db_query_items.append(item)
        tree = Tree.objects.get(id=id)
        persons = Individual.objects.filter(reduce(lambda x, y: x & y, db_query_items) & Q(tree=tree))[:10]

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
    family_choices.append((0, f'{this_person} and unknown partner'))

    if request.method == 'POST':
        if request.POST.get('identifier') == 'add_new_child':
            form = AddPersonChildForm(request.POST)
            form.fields['family'].choices = family_choices
            search_form = AddExistingPersonChildForm(tree_id=this_person.tree.id)
            search_form.fields['family'].choices = family_choices
            if form.is_valid():
                cd = form.cleaned_data
                child = Individual()
                child.tree = this_person.tree
                child.first_name = cd['first_name']
                child.last_name = cd['last_name']
                child.birth_place = cd['birth_place']
                child.birth_date = cd['birth_date']
                child.death_place = cd['death_place']
                child.death_date = cd['death_date']
                child.sex = cd['sex']
                child.save()

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

            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response

        elif request.POST.get('identifier') == 'add_existing_person':
            form = AddPersonChildForm()
            form.fields['family'].choices = family_choices
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
                print(search_form.errors)
                response = JsonResponse({'errors': dict(search_form.errors)}, status=400)
                return response

    else:
        form = AddPersonChildForm()
        form.fields['family'].choices = family_choices
        search_form = AddExistingPersonChildForm(tree_id=this_person.tree.id)
        search_form.fields['family'].choices = family_choices

    title = f'Add Child for {this_person}'

    return render(request, 'genealogy/add_new_existing_person_modal.html', {'form': form, 'search_form': search_form, 'modal_title': title})

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
            form = AddPersonForm(request.POST)
            search_form = FindExistingPersonForm(tree_id=this_person.tree.id)
            if form.is_valid():
                cd = form.cleaned_data

                new_parent = Individual()
                new_parent.tree = this_person.tree
                new_parent.first_name = cd['first_name']
                new_parent.last_name = cd['last_name']
                new_parent.birth_place = cd['birth_place']
                new_parent.birth_date = cd['birth_date']
                new_parent.death_place = cd['death_place']
                new_parent.death_date = cd['death_date']
                new_parent.sex = cd['sex']
                new_parent.save()

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

            else:
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
        elif request.POST.get('identifier') == 'add_existing_person':
            form = AddPersonForm()
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
                response = JsonResponse({'errors': dict(form.errors)}, status=400)
                return response
    else:
        form = AddPersonForm()
        search_form = FindExistingPersonForm(tree_id=this_person.tree.id)

    if parent == 'father':
        title = f'Add Father for {this_person}'
    else:
        title = f'Add Mother for {this_person}'

    return render(request, 'genealogy/add_new_existing_person_modal.html', {'form': form, 'search_form': search_form, 'modal_title': title})

@login_required
def add_person(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")

    if request.method == 'POST':
        form = AddPersonForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if cd['first_name'] or cd['last_name']:
                new_person = Individual()
                new_person.tree = this_tree
                new_person.first_name = cd['first_name']
                new_person.last_name = cd['last_name']
                new_person.birth_place = cd['birth_place']
                new_person.birth_date = cd['birth_date']
                new_person.death_place = cd['death_place']
                new_person.death_date = cd['death_date']
                new_person.sex = cd['sex']
                new_person.save()

                messages.success(request, 'New person added successfully!')

                return HttpResponse(status=204)
            else:
                errors = {'name': 'A person needs at least a first name or last name!'}
                response = JsonResponse({'errors': errors}, status=400)
                return response
        else:
            response = JsonResponse({'errors': dict(form.errors)}, status=400)
            return response            
    else:
        form = AddPersonForm()

    title = 'Add New Person'

    return render(request, 'genealogy/add_new_person_modal.html', {'form' : form, 'modal_title': title})

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
                form = AddEventForm()
                return render(request, 'genealogy/add_event_modal.html', {'person': this_person, 'form': form, 'event_type': event_type_text})
            elif any(e[0] == event_type for e in FamilyEvent.EVENT_TYPES):
                form = AddFamilyEventForm()
                families = Family.objects.filter(Q(husband=this_person) | Q(wife=this_person) & Q(husband__isnull=False) & Q(wife__isnull=False))
                if not families:
                    errors = {'no_families': 'No families found for this person. First add a partner before adding family events!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response

                form.fields['family'].choices = [(family.id, family) for family in families]

                return render(request, 'genealogy/add_event_modal.html', {'person': this_person, 'form': form, 'event_type': event_type_text})
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
                if cd['date'] and this_person.birth_year and extract_year(cd['date']) < this_person.birth_year:
                    errors = {'date': 'Event date is before birth date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                if cd['date'] and this_person.death_year and extract_year(cd['date']) > this_person.death_year:
                    errors = {'date': 'Event date is after death date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                cd = form.cleaned_data
                event = Event()
                event.indi = this_person
                event.event_type = event_type
                event.date = cd['date']
                event.place = cd['place']
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
                if cd['date'] and this_person.birth_year and extract_year(cd['date']) < this_person.birth_year:
                    errors = {'date': 'Event date is before birth date!'}
                    response = JsonResponse({'errors': errors}, status=400)
                    return response
                if cd['date'] and this_person.death_year and extract_year(cd['date']) > this_person.death_year:
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
def get_tree_list(request):
    trees = Tree.objects.filter(user=request.user)
    trees = trees.annotate(number_of_individuals=Count("individuals"))

    return render(request, 'genealogy/tree_list.html', {'trees': trees})

@login_required
def view_tree(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
        if this_tree.user != request.user:
            raise Http404("Tree not found for this user.")
    except Tree.DoesNotExist:
        raise Http404("Tree does not exist.")
    
    this_tree.number_of_individuals = Tree.objects.filter(id=id).annotate(number_of_individuals=Count("individuals")).values_list("number_of_individuals", flat=True).first()

    return render(request, 'genealogy/view_tree.html', {'section': 'family_tree', 'tree': this_tree})

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