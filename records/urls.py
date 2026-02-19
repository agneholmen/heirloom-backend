from django.urls import include, path
from . import views

app_name = "records"
urlpatterns = [
    path('', views.home, name='home'),
    # API endpoints
    path('api/records/', views.RecordListView.as_view(), name='record-list'),
    path('api/records/<int:pk>/', views.RecordDetailView.as_view(), name='record-detail'),
    path('api/birth-records/', views.BirthRecordSearchView.as_view(), name='birth-record-search'),
    path('api/birth-records/<int:pk>/', views.BirthRecordDetailView.as_view(), name='birth-record-detail'),
]