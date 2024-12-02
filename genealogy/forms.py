from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .models import Individual, Profile, Tree

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Layout, Submit, Div, Field, Row, Column


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
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

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
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'photo', 'description', 'sex']

class UploadFileForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        data = self.cleaned_data['file']
        if not data.name.endswith('.ged'):
            raise forms.ValidationError('The uploaded file must be a .ged file.')
        return data

class NewTreeForm(forms.Form):
    name = forms.CharField(
        label="Name",
        required=True
    )


class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'GET'
        self.helper.form_action = reverse_lazy('search')
        self.helper.add_input(Submit('submit', 'Search'))
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

class EditPersonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row('first_name', css_class="form-outline mb4"),
            Row('last_name', css_class="form-outline mb4"),
            Row('birth_date', css_class="form-outline mb4"),
            Row('death_date', css_class="form-outline mb4"),
            Row(
                Column(Submit('submit', 'Save Changes', css_class="btn btn-primary", data_bs_dismiss="modal")),
                Column(Button('cancel', 'Cancel', css_class="btn btn-secondary", data_bs_dismiss="modal")),
                css_class="form-outline mb4"
            )
        )

    class Meta:
        model = Individual
        fields = ['first_name', 'last_name', 'birth_date', 'death_date']
