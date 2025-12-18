from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import PersonSearchView, PersonViewSet, TreeViewSet

app_name = 'api'

router = DefaultRouter()
router.register(r'trees', TreeViewSet, basename='tree')

persons_router = NestedDefaultRouter(router, r'trees', lookup='tree')
persons_router.register(r'persons', PersonViewSet, basename='tree-persons')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(persons_router.urls)),
    path('search/', view=PersonSearchView.as_view(), name='person-search'),
]