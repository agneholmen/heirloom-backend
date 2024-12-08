from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import render, redirect
from .forms import (
    EditPersonForm,
    EditTreeForm,
    LoginForm,
    NewTreeForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    SearchForm
)
from .models import (
    Child,
    Family,
    Individual, 
    Profile, 
    Tree
)

from . import gedcom

from django_htmx.http import trigger_client_event

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

    trees = Tree.objects.filter(user=request.user)
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
    trees = Tree.objects.filter(user=request.user)

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
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")

    trees = Tree.objects.filter(user=request.user)
    if this_person.tree not in trees:
        raise Http404("Individual not found in any of your trees.")

    father = None
    mother = None
    siblings = None
    families = None
    children_objects = Child.objects.filter(indi=this_person)
    if children_objects:
        # Needs fixing later to handle if it belongs to multiple families. For now I'll just take the first item.
        father = children_objects[0].family.husband
        mother = children_objects[0].family.wife

        siblings = Child.objects.filter(family=children_objects[0].family).exclude(id=children_objects[0].id)
    
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
            'families': families
        }
    )

@login_required
def edit_person(request, id):
    try:
        this_person = Individual.objects.get(id=id)
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
def delete_person(request, id):
    try:
        this_person = Individual.objects.get(id=id)
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
def delete_tree(request, id):
    try:
        this_tree = Tree.objects.get(id=id)
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
def get_tree_list(request):
    trees = Tree.objects.filter(user=request.user)
    trees = trees.annotate(number_of_individuals=Count("individuals"))

    return render(request, 'genealogy/tree_list.html', {'trees': trees})

@login_required
def view_tree(request, id):
    return render(request, 'genealogy/view_tree.html', {'section': 'family_tree'})

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
    except Individual.DoesNotExist:
        raise Http404("Individual does not exist.")
    
    return render(
        request,
        'genealogy/search_result_row.html',
        {'person': this_person}
    )