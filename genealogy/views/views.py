from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from ..models import Image, Tree

User = get_user_model()

@login_required
def home(request):
    return render(
        request,
        'genealogy/home.html',
        {
            'section': 'home'
        }
    )

@login_required
def community(request):
    users = User.objects.all().exclude(id=request.user.id)
    followers = request.user.followers.all()

    return render(
        request,
        'genealogy/community.html',
        {
            'section': 'community',
            'users': users,
            'followers': followers
        }
    )

@login_required
def community_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    followers = user.followers.all()
    trees = Tree.objects.filter(user=user, private=False)
    trees = trees.annotate(number_of_persons=Count("persons"))
    images = Image.objects.filter(user=user, private=False)

    return render(
        request,
        'genealogy/community_user.html',
        {
            'section': 'community',
            'user': user,
            'followers': followers,
            'trees': trees,
            'images': images
        }
    )

@login_required
def follow_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.user in user.followers.all():
        request.user.unfollow(user)
        response_data = {'status': 'unfollowed', 'number_of_followers': user.followers.count()}
    else:
        request.user.follow(user)
        response_data = {'status': 'followed', 'number_of_followers': user.followers.count()}

    return JsonResponse(status=200, data=response_data)