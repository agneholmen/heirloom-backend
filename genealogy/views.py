from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render
from .forms import (
    LoginForm, 
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    SearchForm,
    UploadFileForm
)
from .models import (
    Child,
    Family,
    Individual, 
    Profile, 
    Tree
)

from . import gedcom

from functools import reduce

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
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            new_tree = Tree(user=request.user, gedcom_file=request.FILES["file"])
            new_tree.save()
            gedcom.handle_uploaded_file(new_tree)

    else:
        form = UploadFileForm()

    trees = Tree.objects.filter(user=request.user)

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
        search_form = SearchForm(request.GET)
        search_form.fields["tree"].queryset = trees
        if search_form.is_valid():
            cd = search_form.cleaned_data
            
            and_condition = Q(tree=cd['tree'])
            or_conditions = []
            if cd['name']:
                or_conditions.append(Q(first_name__icontains=cd['name']))
                or_conditions.append(Q(last_name__icontains=cd['name']))
            if cd['birth_place']:
                or_conditions.append(Q(birth_place__icontains=cd['birth_place']))
            if cd['birth_date']:
                or_conditions.append(Q(birth_date__icontains=cd['birth_date']))
            if cd['death_place']:
                or_conditions.append(Q(death_place__icontains=cd['death_place']))
            if cd['death_date']:
                or_conditions.append(Q(death_date__icontains=cd['death_date']))

            combined_or_conditions = reduce(lambda x, y: x | y, or_conditions)

            final_query = combined_or_conditions & and_condition

            people = Individual.objects.filter(final_query)

            return render(
                request,
                'genealogy/search.html',
                {
                    'section': 'search',
                    'trees': trees,
                    'search_form': search_form,
                    'people': people
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
    children = Child.objects.filter(indi=this_person)
    if children:
        father = children[0].family.husband
        mother = children[0].family.wife

        siblings = Child.objects.filter(family=children[0].family).exclude(id=children[0].id)


    return render(
        request,
        'genealogy/person.html',
        {
            'section': 'search',
            'person': this_person,
            'father': father,
            'mother': mother,
            'siblings': siblings
        }
    )

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