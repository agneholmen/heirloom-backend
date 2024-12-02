from django.contrib.auth import views as auth_views
from django.urls import include, path
from . import views

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('', views.home, name='home'),
    path('images/', views.images, name='images'),
    path('search/', views.search, name='search'),
    path('family_tree/', views.family_tree, name='family_tree'),
    path('register/', views.register, name='register'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('person/<int:id>', views.person, name='person'),
    path('edit_person/<int:id>', views.edit_person, name='edit_person'),
    path('update_result_row/<int:id>', views.update_result_row, name='update_result_row'),
]