from django.contrib.auth import views as auth_views
from django.urls import include, path
from . import views

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('', views.home, name='home'),
    path('images/', views.images, name='images'),
    path('search/', views.search, name='search'),
    path('register/', views.register, name='register'),
    path('profile/edit', views.edit_profile, name='edit_profile'),
    path('person/<int:id>', views.person, name='person'),
    path('person/<int:id>/edit', views.edit_person, name='edit_person'),
    path('person/<int:id>/delete', views.delete_person, name='delete_person'),
    path('person/<int:id>/add/partner', views.add_person_as_partner, name='add_person_as_partner'),
    path('person/<int:id>/add/child', views.add_person_as_child, name='add_person_as_child'),
    path('person/<int:id>/add/parent/<str:parent>', views.add_person_as_parent, name='add_person_as_parent'),
    path('search/update-result-row/<int:id>', views.update_search_result_row, name='update_result_row'),
    path('tree/', views.family_tree, name='family_tree'),
    path('tree/<int:id>/view', views.view_tree, name='view_tree'),
    path('tree/<int:id>/delete', views.delete_tree, name='delete_tree'),
    path('tree/<int:id>/edit', views.edit_tree, name='edit_tree'),
    path('tree/<int:id>/add-person', views.add_person, name='add_person'),
    path('tree/get-list', views.get_tree_list, name='get_tree_list'),
]