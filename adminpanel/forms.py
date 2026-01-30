from django import forms
from hr.models import HR
import re

class HRRegistrationForm(forms.ModelForm):
    # Designation choices based on field
    IT_DESIGNATIONS = [
        'Software Developer', 'Java Developer', 'Python Developer', 'Frontend Developer',
        'Backend Developer', 'Full Stack Developer', 'DevOps Engineer', 'Data Scientist',
        'Machine Learning Engineer', 'UI/UX Designer', 'QA Engineer', 'System Administrator',
        'Database Administrator', 'Network Engineer', 'Cloud Engineer', 'Mobile Developer',
        'React Developer', 'Angular Developer', 'Node.js Developer', 'PHP Developer'
    ]
    
    NON_IT_DESIGNATIONS = [
        'Marketing Executive', 'HR Manager', 'Sales Executive', 'Business Analyst',
        'Project Manager', 'Content Writer', 'Digital Marketing Specialist', 'SEO Specialist',
        'Social Media Manager', 'Customer Service Representative', 'Account Manager',
        'Operations Manager', 'Finance Manager', 'Administrative Assistant', 'Event Manager',
        'Public Relations Officer', 'Brand Manager', 'Market Research Analyst',
        'Business Development Executive', 'Product Manager'
    ]
    
    # Override fields to add custom widgets and validation
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        })
    )
    
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    years_of_experience = forms.IntegerField(
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Years of experience'
        })
    )
    
    specialization_skills = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'e.g., Full-stack hiring, campus recruitment, technical interviews'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set initial password (min 6 chars)'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    designations_handled = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'designation-checkboxes'
        })
    )
    
    class Meta:
        model = HR
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'gender',
            'date_of_birth', 'field_of_expertise', 'designations_handled',
            'years_of_experience', 'specialization_skills'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up designation choices based on field of expertise
        # Populate with all options; clean() will validate based on field
        self.fields['designations_handled'].choices = [
            (d, d) for d in (self.IT_DESIGNATIONS + self.NON_IT_DESIGNATIONS)
        ]
        
        # Add JavaScript to dynamically update designations
        self.fields['field_of_expertise'].widget.attrs.update({
            'class': 'form-control',
            'onchange': 'updateDesignations()'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if HR.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        from datetime import date
        if not dob:
            return dob
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 26:
            raise forms.ValidationError('HR must be at least 26 years old.')
        return dob
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Basic phone validation
        if not re.match(r'^\+?1?\d{9,15}$', phone):
            raise forms.ValidationError("Please enter a valid phone number")
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        field_of_expertise = cleaned_data.get('field_of_expertise')
        designations_handled = cleaned_data.get('designations_handled') or []
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        
        # Validate designations based on field
        if field_of_expertise == 'IT':
            valid_designations = self.IT_DESIGNATIONS
        else:
            valid_designations = self.NON_IT_DESIGNATIONS
        
        for designation in designations_handled:
            if designation not in valid_designations:
                raise forms.ValidationError(
                    f"'{designation}' is not a valid designation for {field_of_expertise} field"
                )

        # Password validation
        if not password or not confirm:
            raise forms.ValidationError('Password and Confirm Password are required.')
        if len(password) < 6:
            self.add_error('password', 'Password must be at least 6 characters.')
        if password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        
        return cleaned_data


class HREditForm(forms.ModelForm):
    IT_DESIGNATIONS = HRRegistrationForm.IT_DESIGNATIONS
    NON_IT_DESIGNATIONS = HRRegistrationForm.NON_IT_DESIGNATIONS

    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    years_of_experience = forms.IntegerField(
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Years of experience'})
    )
    specialization_skills = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Specializations and skills'})
    )
    designations_handled = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'designation-checkboxes'})
    )

    class Meta:
        model = HR
        fields = [
            'phone_number', 'date_of_birth', 'years_of_experience',
            'specialization_skills', 'designations_handled'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate designation options based on HR field_of_expertise
        hr_instance = self.instance
        if hr_instance and hr_instance.field_of_expertise == 'IT':
            options = self.IT_DESIGNATIONS
        else:
            options = self.NON_IT_DESIGNATIONS
        self.fields['designations_handled'].choices = [(d, d) for d in options]

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^\+?1?\d{9,15}$', phone):
            raise forms.ValidationError('Please enter a valid phone number')
        return phone