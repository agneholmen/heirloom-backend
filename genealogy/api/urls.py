from django.urls import path
from .views import TreeView

app_name = 'api'

urlpatterns = [
    path('trees/', TreeView.as_view(), name='trees'),
]