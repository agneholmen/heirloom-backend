from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q
from .models import Record, BirthRecord
from .serializers import RecordSerializer, BirthRecordSerializer


def home(request):
    return HttpResponse("Home page")


class RecordListView(generics.ListAPIView):
    """List all historical record sources"""
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class RecordDetailView(generics.RetrieveAPIView):
    """Get details of a specific record source"""
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class BirthRecordSearchView(generics.ListAPIView):
    """Search birth records with various filters"""
    serializer_class = BirthRecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = BirthRecord.objects.select_related('record')
        
        # Get query parameters
        first_name = self.request.query_params.get('first_name', None)
        sex = self.request.query_params.get('sex', None)
        birth_year = self.request.query_params.get('birth_year', None)
        birth_year_from = self.request.query_params.get('birth_year_from', None)
        birth_year_to = self.request.query_params.get('birth_year_to', None)
        location = self.request.query_params.get('location', None)
        father_last_name = self.request.query_params.get('father_last_name', None)
        mother_last_name = self.request.query_params.get('mother_last_name', None)
        record_id = self.request.query_params.get('record', None)
        
        # Apply filters
        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        
        if sex:
            queryset = queryset.filter(sex=sex)
        
        if birth_year:
            queryset = queryset.filter(birth_year=birth_year)
        
        if birth_year_from:
            queryset = queryset.filter(birth_year__gte=birth_year_from)
        
        if birth_year_to:
            queryset = queryset.filter(birth_year__lte=birth_year_to)
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if father_last_name:
            queryset = queryset.filter(father_last_name__icontains=father_last_name)
        
        if mother_last_name:
            queryset = queryset.filter(mother_last_name__icontains=mother_last_name)
        
        if record_id:
            queryset = queryset.filter(record_id=record_id)
        
        return queryset.order_by('birth_year', 'first_name')


class BirthRecordDetailView(generics.RetrieveAPIView):
    """Get details of a specific birth record"""
    queryset = BirthRecord.objects.select_related('record')
    serializer_class = BirthRecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

