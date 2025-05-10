from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

User = get_user_model()

from .forms import (
    LoginForm,
    UserEditForm,
    UserRegistrationForm
)

@login_required
def home(request):
    return render(
        request,
        'genealogy/home.html',
        {
            'section': 'home'
        }
    )

# Is this used?
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
            return render(
                request,
                'users/register_done.html',
                {'new_user': new_user}
            )
    else:
        user_form = UserRegistrationForm()
    return render(
        request,
        'users/register.html',
        {'user_form': user_form}
    )

@login_required
def edit_user(request):
    if request.method == 'POST':
        user_form = UserEditForm(
            instance=request.user,
            data=request.POST,
            files=request.FILES
        )
        if user_form.is_valid():
            user_form.save()
            messages.success(
                request,
                'User updated successfully!'
            )
        else:
            messages.error(request, 'Error updating your user information!')

    else:
        user_form = UserEditForm(instance=request.user)

    return render(
        request,
        'users/edit_user.html',
        {
            'user_form': user_form,
            'section': 'edit_user'
        }
    )