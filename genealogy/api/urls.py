from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import PersonSearchView, TreeViewSet

app_name = 'api'

router = DefaultRouter()
router.register(r'trees', TreeViewSet, basename='tree')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', view=PersonSearchView.as_view(), name='person-search'),
]