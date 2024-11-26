from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from .models import Profile, Tree


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
    tree = forms.ModelChoiceField(
        queryset=Tree.objects.none(),  # Set initial queryset as empty
        required=True,
        blank=False,
        label="Select Tree",
        empty_label=None
    )

    name = forms.CharField(
        label="Name",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter name"})
    )

    birth_place = forms.CharField(
        label="Birth Place",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter birth place"})
    )

    birth_date = forms.CharField(
        label="Birth Date",
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter birth year"})
    )

    birth_year_start = forms.IntegerField(
        label="Birth Year Start",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter earliest possible birth year"})
    )

    birth_year_end = forms.IntegerField(
        label="Birth Year End",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter latest possible birth year"})
    )

    death_place = forms.CharField(
        label="Death Place",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter death place"})
    )

    death_date = forms.CharField(
        label="Death Date",
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter death date"})
    )

    death_year_start = forms.IntegerField(
        label="Death Year Start",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter earliest possible death year"})
    )

    death_year_end = forms.IntegerField(
        label="Death Year End",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter latest possible death year"})
    )