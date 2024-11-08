from django.contrib.auth import views as auth_views
from django.urls import include, path
from . import views

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('', views.home, name='home'),
    path('images/', views.images, name='images'),
    path('search/', views.search, name='search'),
    path('family_tree/', views.family_tree, name='family_tree'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
]