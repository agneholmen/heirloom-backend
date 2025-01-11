from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from datetime import date

from .date_functions import extract_year

def users_file_location(instance, filename):
    date_string = date.today().strftime("%Y/%m/%d")
    return f"users/{instance.user.username}/{date_string}/{filename}"


class Profile(models.Model):
    SEX_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("U", "Unknown"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to=users_file_location,
        blank=True
    )
    description = models.TextField(blank=True, null=True)
    sex = models.CharField(
        max_length=1,
        choices=SEX_CHOICES,
        default="U"
    )

    def __str__(self) -> str:
        return f'Profile of {self.user.username}'
    

class Tree(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    upload_date = models.DateField(default=date.today)
    name = models.CharField(
        max_length=100
    )
    description = models.CharField(
        blank=True,
        null=True,
        max_length=200
    )
    gedcom_file = models.FileField(
        upload_to=users_file_location,
        blank=True,
        null=True
    )

    def clean(self):
        if Tree.objects.filter(user=self.user, name=self.name).exclude(id=self.id).exists():
            raise ValidationError({'name': 'A tree with that name already exists.'})
        if not self.name:
            raise ValidationError({'name': 'A tree needs to have a name.'})

    def __str__(self) -> str:
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='User and name combination')
        ]

class Individual(models.Model):
    SEX_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("U", "Unknown"),
    )

    indi_id = models.CharField(max_length=20, null=True, blank=True)
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE, related_name="individuals")
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, default="U")
    birth_date = models.CharField(max_length=100, null=True, blank=True)
    birth_place = models.CharField(max_length=100, null=True, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    death_date = models.CharField(max_length=100, null=True, blank=True)
    death_place = models.CharField(max_length=100, null=True, blank=True)
    death_cause = models.CharField(max_length=100, null=True, blank=True)
    death_year = models.PositiveSmallIntegerField(null=True, blank=True)
    alive = models.BooleanField(default=False)
    added = models.DateField(auto_now_add=True)
    last_updated = models.DateField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tree', 'indi_id'], name='Tree and INDI combination')
        ]
        ordering = ['last_name']

    def get_name_years(self):
        string = ""
        if self.first_name:
            string += self.first_name
        if self.last_name:
            string += f" {self.last_name}"
        if self.birth_year or self.death_year:
            if self.birth_year and self.death_year:
                string += f" ({self.birth_year} - {self.death_year})"
            elif self.birth_year:
                string += f" ({self.birth_year} - )"
            else:
                string += f" ( - {self.death_year})"

        return string
    
    def get_name_years_event(self):
        string = ""
        if self.first_name:
            string += self.first_name
        if self.last_name:
            string += f" {self.last_name}"

        birth = self.get_birth_event()
        death = self.get_death_event()

        if (birth and birth.year) and (death and death.year):
            string += f" ({birth.year} - {death.year})"
        elif birth and birth.year:
            string += f" ({birth.year} - )"
        elif death and death.year: 
            string += f" ( - {death.year})"

        return string

    def get_birth_event(self):
        try:
            return Event.objects.get(indi=self, event_type='birth')
        except Event.DoesNotExist:
            return None
        
    def get_death_event(self):
        try:
            return Event.objects.get(indi=self, event_type='death')
        except Event.DoesNotExist:
            return None

    def __str__(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))
    
    def save(self, *args, **kwargs):
        if self.birth_date:
            self.birth_year = extract_year(self.birth_date)
        if self.death_date:
            self.death_year = extract_year(self.death_date)

        super().save(*args, **kwargs)
    

class Family(models.Model):
    family_id = models.CharField(max_length=20, null=True, blank=True)
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE)
    husband = models.ForeignKey(
        Individual,
        on_delete=models.SET_NULL,
        related_name="families_as_husband",
        null=True,
        blank=True
    )
    wife = models.ForeignKey(
        Individual,
        on_delete=models.SET_NULL,
        related_name="families_as_wife",
        null=True,
        blank=True
    )

    def clean(self):
        if self.husband and self.husband.tree != self.tree:
            raise ValidationError("Husband must belong to the same tree as the family.")
        if self.wife and self.wife.tree != self.tree:
            raise ValidationError("Wife must belong to the same tree as the family.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.husband and self.wife:
            return f"{self.husband} and {self.wife}"
        elif self.husband:
            return f"{self.husband} and unknown mother"
        else:
            return f"{self.wife} and unknown father"

    class Meta:
        verbose_name_plural = "Families"

class Child(models.Model):
    RELATIONS = (
        ("A", "Adopted"),
        ("B", "Biological"),
        ("F", "Foster"),
        ("U", "Unknown"),
    )

    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"                   
    )
    indi = models.ForeignKey(
        Individual,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    relation = models.CharField(
        choices=RELATIONS,
        max_length=1,
        default="B"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['family', 'indi'], name='Individual and family combination')
        ]
        verbose_name_plural = "Children"


class Event(models.Model):
    EVENT_TYPES = [
        ('baptism', 'Baptism'),
        ('confirmation', 'Confirmation'),
        ('cremation', 'Cremation'),
        ('emigration', 'Emigration'),
        ('funeral', 'Funeral'),
        ('graduation', 'Graduation'),
        ('immigration', 'Immigration'),
        ('residence', 'Place of Residence'),
        ('birth', 'Birth'),
        ('death', 'Death'),
        # Add other event types as needed
    ]

    indi = models.ForeignKey(Individual, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    date = models.CharField(max_length=100, null=True, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def clean(self):
        if self.event_type == 'birth' and Event.objects.filter(indi=self.indi, event_type='birth').exists():
            raise ValidationError("An individual can only have one birth event.")
        if self.event_type == 'death' and Event.objects.filter(indi=self.indi, event_type='death').exists():
            raise ValidationError("An individual can only have one death event.")

    def save(self, *args, **kwargs):
        if self.date:
            self.year = extract_year(self.date)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_event_type_display()} for {self.indi}"
    

class FamilyEvent(models.Model):
    EVENT_TYPES = [
        ('banns', 'Banns'),
        ('divorce', 'Divorce'),
        ('engagement', 'Engagement'),
        ('marriage', 'Marriage'),
    ]

    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    date = models.CharField(max_length=100, null=True, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.date:
            self.year = extract_year(self.date)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_event_type_display()} for {self.family}"


# Handle cleanup of family, so there are no families with only one person and no children
# or families with only children
@receiver(pre_delete, sender=Individual)
def handle_family_cleanup(sender, instance, **kwargs):
    families = Family.objects.filter(models.Q(husband=instance) | models.Q(wife=instance))
    for family in families:
        has_children = Child.objects.filter(family=family).exists()
        if not has_children:
            family.delete()
        if (family.husband == instance and not family.wife) or (family.wife == instance and not family.husband):
            print(family)
            family.delete()

# Removes the GEDCOM file when you remove a Tree instance
@receiver(post_delete, sender=Tree)
def tree_post_delete_handler(sender, **kwargs):
    tree = kwargs['instance']
    if hasattr(tree, 'gedcome_file'):
        storage, path = tree.gedcom_file.storage, tree.gedcom_file.path
        storage.delete(path)