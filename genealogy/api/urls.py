from django.urls import path
from .views import TreeView

app_name = 'api'

urlpatterns = [
    path('trees/', TreeView.as_view(), name='tree-list'),
    path('trees/<int:pk>/', TreeView.as_view(), name='tree-detail'),
]