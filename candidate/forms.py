from django import forms
from django.contrib.auth.models import User
from .models import CandidateProfile
from datetime import date
import re

class UserRegisterForm(forms.ModelForm):
    name = forms.CharField(max_length=100)
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    email = forms.EmailField()
    email_otp = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 4-digit OTP',
            'class': 'form-control',
            'pattern': '[0-9]{4}'
        }),
        required=False  # Initially not required, will be validated in clean()
    )
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['name', 'dob', 'email', 'password']

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[A-Za-z ]+$', name):
            raise forms.ValidationError("Only characters allowed in name.")
        return name

    def clean_dob(self):
        dob = self.cleaned_data['dob']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 21:
            raise forms.ValidationError("You must be at least 21 years old.")
        return dob

    def clean_email(self):
        email = self.cleaned_data['email']
        # Don't check if email exists here - the email confirmation flow handles this
        # This allows the registration form to work with pre-filled emails from OTP verification
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        email_otp = cleaned_data.get("email_otp")

        if password and len(password) < 6:
            self.add_error("password", "Password must be at least 6 characters.")
        if password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        
        # Email OTP validation will be handled in the view
        return cleaned_data

class EmailConfirmationForm(forms.Form):
    """Form for requesting email confirmation OTP"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'form-control'
        })
    )

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your registered email address',
            'class': 'form-control'
        })
    )

class PasswordResetConfirmForm(forms.Form):
    otp = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 4-digit OTP',
            'class': 'form-control',
            'pattern': '[0-9]{4}'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter new password',
            'class': 'form-control'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'class': 'form-control'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and len(new_password) < 6:
            self.add_error("new_password", "Password must be at least 6 characters.")
        if new_password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['resume']

#designation selection
class DesignationForm(forms.Form):
    DESIGNATION_CHOICES = {
        'IT': [
            'Python Developer', 'Java Developer', 'Web Developer',
            'Software Engineer', 'Data Analyst', 'DevOps Engineer',
            'Machine Learning Engineer', 'Full Stack Developer',
            'Android Developer', 'Frontend Developer', 'Backend Developer',
            'System Administrator'
        ],
        'Non-IT': [
            'HR Executive', 'Sales Executive', 'Marketing Manager',
            'Business Analyst', 'Customer Support', 'Operations Executive',
            'Accountant', 'Financial Analyst', 'Admin Assistant',
            'Content Writer', 'Recruiter', 'Office Manager'
        ]
    }

    designation = forms.ChoiceField(choices=[])

    def __init__(self, field_type='IT', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['designation'].choices = [
            (d, d) for d in self.DESIGNATION_CHOICES.get(field_type, [])
        ]