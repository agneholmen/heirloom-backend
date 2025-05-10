from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Layout, Submit, Div, Field, Row, Column
from django.contrib.auth import get_user_model

from image_uploader_widget.widgets import ImageUploaderWidget

User = get_user_model()

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('username', css_class="col-md-4"),
                Column('first_name', css_class="col-md-4"),
                Column('last_name', css_class="col-md-4")
            ),
            Row('email', css_class="form-outline mb-1"),
            Row('password', css_class="form-outline mb-1"),
            Row('password2', css_class="form-outline mb-1")
        )

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
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={"placeholder": "Email"}),
        }

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
            Row('email', css_class="form-outline mb-1"),
            Row('date_of_birth', css_class="form-outline mb-1"),
            Row('description', css_class="form-outline mb-1"),
            Row('sex', css_class="form-outline mb-1"),
        )

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'photo', 'description', 'sex']
        widgets = {
            'email': forms.EmailInput(attrs={"placeholder": "Email"}),
            'photo': ImageUploaderWidget(),
            'date_of_birth': forms.DateInput(attrs={"type": "date"}),
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