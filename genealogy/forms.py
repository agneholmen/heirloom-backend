from django import forms
from django.forms import Select
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .models import Event, FamilyEvent, Image, Person, Profile, Tree

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Layout, Submit, Div, Field, Row, Column

from image_uploader_widget.widgets import ImageUploaderWidget

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label='Repeat password',
        widget=forms.PasswordInput
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'email']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Passwords don't match.")
        return cd['password2']
    
    def clean_email(self):
        data = self.cleaned_data['email']
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError('Email already in use.')
        return data
    
class UserEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class="col-md-4"),
                Column('last_name', css_class="col-md-4")
            ),
            Row('email', css_class="form-outline mb-1")
        )

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={"placeholder": "Email"}),
        }

    def clean_email(self):
        data = self.cleaned_data['email']
        qs = User.objects.exclude(
            id=self.instance.id
        ).filter(
            email=data
        )
        if qs.exists():
            raise forms.ValidationError('Email already in use.')
        return data

class ProfileEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('date_of_birth', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1"),
            Row('sex', css_class="form-outline mb-1"),
        )

    class Meta:
        model = Profile
        fields = ['date_of_birth', 'photo', 'description', 'sex']
        widgets = {
            'photo': ImageUploaderWidget(),
            'date_of_birth': forms.DateInput(attrs={"type": "date"}),
        }

class NewTreeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy('family_tree')
        self.helper.add_input(Submit('upload-submit', 'Create Tree', css_id='upload-button'))
        self.helper.layout = Layout(
            Row(
                Column('file', css_class='col-md-4'),
                Column('name', css_class='col-md-4')
            ),
            Row(
                Column('description', css_class='col-md-8')
            )
        )

    file = forms.FileField(
        required=False,
        label="GEDCOM file"
    )
    name = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Name of the tree"})
    )
    description = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Enter a short description"})
    )

    def clean_file(self):
        if not self.cleaned_data['file']:
            return None
        data = self.cleaned_data['file']
        if not data.name.endswith('.ged'):
            raise forms.ValidationError('The uploaded file must be a .ged file.')
        return data

class EditTreeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('name', css_class="form-outline mb12"),
            Row('description', css_class="form-outline mb12"),
            Row(
                Column(Submit('edit-submit', 'Save', css_id='edit-button', css_class='btn btn-primary')),
                Column(Button('cancel-edit', 'Cancel', css_class='btn btn-secondary'), data_bs_dismiss="modal"),
                css_class='form-outline mb12'
            )
        )

    class Meta:
        model = Tree
        fields = ['name', 'description']

class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'GET'
        self.helper.form_action = reverse_lazy('search')
        self.helper.add_input(Submit('search-submit', 'Search', css_id='search-button'))
        self.helper.layout = Layout(
            Row(
                Column('tree', css_class='col-md-4'),
                Column('results_per_page', css_class='col-md-4')
            ),
            Row(
                Column('name', css_class='col-md-4'),
                Column('birth_place', css_class='col-md-4'),
                Column('death_place', css_class='col-md-4')
            ),
            Row(
                Column('birth_date', css_class='col-md-4'),
                Column('birth_year_start', css_class='col-md-4'),
                Column('birth_year_end', css_class='col-md-4')
            ),
            Row(
                Column('death_date', css_class='col-md-4'),
                Column('death_year_start', css_class='col-md-4'),
                Column('death_year_end', css_class='col-md-4')
            )
        )

    tree = forms.ModelChoiceField(
        queryset=Tree.objects.none(),  # Set initial queryset as empty
        required=True,
        blank=False,
        label="Select Tree",
        empty_label=None
    )

    results_per_page = forms.ChoiceField(
        choices=((25, 25), (50, 50), (100, 100)),
        required=True,
        label="Number of search results per page",
        initial=25
    )

    name = forms.CharField(
        label="Name",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Name"})
    )

    birth_place = forms.CharField(
        label="Birth Place",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Birth place"})
    )

    birth_date = forms.CharField(
        label="Birth Date",
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Birth date"})
    )

    birth_year_start = forms.IntegerField(
        label="Birth Year Start",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Earliest possible birth year"})
    )

    birth_year_end = forms.IntegerField(
        label="Birth Year End",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Latest possible birth year"})
    )

    death_place = forms.CharField(
        label="Death Place",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Death place"})
    )

    death_date = forms.CharField(
        label="Death Date",
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Death date"})
    )

    death_year_start = forms.IntegerField(
        label="Death Year Start",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Earliest possible death year"})
    )

    death_year_end = forms.IntegerField(
        label="Death Year End",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Latest possible death year"})
    )

class PersonNamesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('identifier'),
            Row(
                Column('first_name', css_class="form-outline mb-1"),
                Column('last_name', css_class="form-outline mb-1")
            ),
            Row(
                Column('sex', css_class="form-outline mb-1")
            )
        )

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data['first_name'] or cleaned_data['last_name']):
            raise forms.ValidationError('You must provide a first name or last name.')

        return cleaned_data

    class Meta:
        model = Person
        fields = ['first_name', 'last_name', 'sex']
        widgets = {
            'sex': forms.RadioSelect,
        }

    identifier = forms.CharField(initial='', widget=forms.HiddenInput(), required=False)

class ExistingChildrenForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('existing_children', css_class="form-outline mb-1")
            )
        )

    existing_children = forms.TypedMultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        coerce=int,
        label="Include as children to partner"
    )

class PersonNamesFamilyForm(PersonNamesForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(3, Row('family', css_class="form-outline mb-1"))

    family = forms.TypedChoiceField(
        choices=[],  # Set initial queryset as empty
        required=True,
        coerce=int,
        label="Select Family"
    )

class EventShortForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class="form-outline mb-1"),
                Column('place', css_class="form-outline mb-1")
            )
        )
        if self.prefix:
            self.fields['date'].label = f"{self.prefix.capitalize()} Date"
            self.fields['place'].label = f"{self.prefix.capitalize()} Place"

    class Meta:
        model = Event
        fields = ['date', 'place']

class FindExistingPersonForm(forms.Form):
    def __init__(self, *args, tree_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('identifier'),
            Row('person', css_class="form-outline mb-1"),
            Row('selected_person', css_class="form-outline mb-1"),
            Row(
                Column(Submit('submit', 'Add Person', css_class="btn btn-primary")),
                Column(Button('cancel', 'Cancel', css_class="btn btn-secondary", data_bs_dismiss="modal")),
                css_class="form-outline mb12"
            )
        )
        if tree_id:
            self.fields['person'].widget.attrs['hx-post'] = f'/genealogy/tree/{tree_id}/find-for-dropdown'

    person = forms.CharField(widget=forms.TextInput(attrs={
        'hx-trigger': 'keyup[this.value.length > 3] changed delay:500ms',
        'hx-target': '#div_id_selected_person',
        'autocomplete': 'off',
        'hx-swap': 'innerHTML'
    }))

    selected_person = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=True,
        choices=[]
    )

    identifier = forms.CharField(initial='add_existing_person', widget=forms.HiddenInput())

class AddExistingPersonChildForm(FindExistingPersonForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'add_existing_person'
        self.helper.layout.insert(3, Row('family', css_class="form-outline mb-1"))

    family = forms.TypedChoiceField(
        choices=[],  # Set initial queryset as empty
        required=True,
        coerce=int,
        label="Select Family"
    )

class SelectEventForm(forms.Form):
    EVENT_CHOICES = sorted(Event.EVENT_TYPES + FamilyEvent.EVENT_TYPES, key=lambda x: x[1])
    EVENT_CHOICES.insert(0, ('select', 'Select Event Type'))

    event_type = forms.ChoiceField(choices=EVENT_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    def get_event_type_text(self):
        for value, text in self.fields['event_type'].choices:
            if value == self.cleaned_data['event_type']:
                return text
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('event_type', css_class="form-outline mb-1")
        )

class AddEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('identifier'),
            Row('date', css_class="form-outline mb-1"),
            Row('place', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1"),
            Row(
                Column(Submit('submit', 'Add Event', css_class="btn btn-primary")),
                Column(Button('cancel', 'Cancel', css_class="btn btn-secondary", data_bs_dismiss="modal")),
                css_class="form-outline mb12"
            )
        )

    identifier = forms.CharField(initial='add_event', widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data['date'] or cleaned_data['place'] or cleaned_data['description']):
            raise forms.ValidationError('You must fill out at least one of the fields.')

        return cleaned_data

    class Meta:
        model = Event
        fields = ['date', 'place', 'description']

class EditEventForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('identifier'),
            Row('date', css_class="form-outline mb-1"),
            Row('place', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1"),
            Row(
                Column(Submit('submit', 'Save', css_class="btn btn-primary")),
                Column(Submit('delete', 'Delete', css_class="btn btn-danger")),
                Column(Button('cancel', 'Cancel', css_class="btn btn-secondary", data_bs_dismiss="modal")),
                css_class="form-outline mb12"
            )
        )

    identifier = forms.CharField(initial='edit_event', widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data['date'] or cleaned_data['place'] or cleaned_data['description']):
            raise forms.ValidationError('You must fill out at least one of the fields.')

        return cleaned_data

    class Meta:
        model = Event
        fields = ['date', 'place', 'description']

class AddFamilyEventForm(AddEventForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(3, Row('family', css_class="form-outline mb-1"))

    family = forms.TypedChoiceField(
        choices=[],  # Set initial queryset as empty
        required=True,
        coerce=int,
        label="Select Family"
    )

    identifier = forms.CharField(initial='add_family_event', widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data['date'] or cleaned_data['place'] or cleaned_data['description']):
            raise forms.ValidationError('You must fill out at least one of the fields.')

        return cleaned_data

    class Meta:
        model = FamilyEvent
        fields = ['date', 'place', 'description']

class EditFamilyEventForm(EditEventForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(3, Row('family', css_class="form-outline mb-1"))

    family = forms.IntegerField(initial=0, widget=forms.HiddenInput())

    identifier = forms.CharField(initial='edit_family_event', widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data['date'] or cleaned_data['place'] or cleaned_data['description']):
            raise forms.ValidationError('You must fill out at least one of the fields.')

        return cleaned_data

    class Meta:
        model = FamilyEvent
        fields = ['date', 'place', 'description']

class RemoveRelationshipForm(forms.Form):
    relationship_type = forms.CharField(widget=forms.HiddenInput())
    related_person_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('relationship_type'),
            Row('related_person_id')
        )

class ImageAddForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('title', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1")
        )

    def clean_image(self):
        SUPPORTED_FILE_TYPES = ('png', 'jpg', 'jpeg')

        image = self.cleaned_data.get("image", None)
        extension = str(image).split('.')[-1]

        if not image:
            raise forms.ValidationError("You must select a file to upload!")
        
        if extension.lower() not in SUPPORTED_FILE_TYPES:
            raise forms.ValidationError("Only PNG, JPG, and JPEG files are supported!")
        
        return image


    class Meta:
        model = Image
        fields = ['title', 'description', 'image']
        widgets = {
            'image': ImageUploaderWidget(),
        }

class ImageEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('title', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1"),
            Row(Submit('submit', 'Save', css_class='btn btn-primary'), css_class="form-outline mb-1")
        )

    class Meta:
        model = Image
        fields = ['title', 'description']