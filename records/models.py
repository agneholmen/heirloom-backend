from django.db import models


class Record(models.Model):
    """Represents a historical record source (e.g., a parish birth book)"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=255, blank=True, help_text="Archive or repository")
    date_range = models.CharField(max_length=100, blank=True, help_text="e.g., 1783-1823")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class BirthRecord(models.Model):
    """Individual birth record entry from historical parish records"""
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unknown'),
    ]

    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='birth_records')
    
    # Person information
    first_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='U')
    birth_date = models.CharField(max_length=20, blank=True, help_text="Full or partial date")
    birth_year = models.SmallIntegerField()
    location = models.CharField(max_length=200, blank=True, help_text="Birth location")
    
    # Father information
    father_first_name = models.CharField(max_length=100, blank=True)
    father_last_name = models.CharField(max_length=100, blank=True)
    father_birth_year = models.SmallIntegerField(null=True, blank=True)
    father_birth_parish = models.CharField(max_length=200, blank=True)
    
    # Mother information
    mother_first_name = models.CharField(max_length=100, blank=True)
    mother_last_name = models.CharField(max_length=100, blank=True)
    mother_birth_year = models.SmallIntegerField(null=True, blank=True)
    mother_birth_parish = models.CharField(max_length=200, blank=True)
    
    # Archive details
    archive_info = models.TextField(blank=True)
    link = models.URLField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['birth_year', 'first_name']
        indexes = [
            models.Index(fields=['birth_year']),
            models.Index(fields=['first_name']),
            models.Index(fields=['father_last_name']),
            models.Index(fields=['mother_last_name']),
        ]

    def __str__(self):
        return f"{self.first_name} ({self.birth_year})"

