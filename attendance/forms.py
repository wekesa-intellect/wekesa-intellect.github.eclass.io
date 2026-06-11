from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import AttendanceSession, Course, EnrollmentRequest, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class SessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['course', 'duration_minutes', 'session_type', 'meeting_link',
                  'require_location', 'latitude', 'longitude', 'allowed_radius']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 120}),
            'session_type': forms.Select(attrs={'class': 'form-control', 'id': 'sessionType'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://meet.google.com/... (optional)'}),
            'require_location': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'id': 'latitude'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'id': 'longitude'}),
            'allowed_radius': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 1000, 'value': 100}),
        }

    def __init__(self, lecturer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.filter(lecturer=lecturer)
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['meeting_link'].required = False


class CodeForm(forms.Form):
    code = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit code'}))


class CourseEnrollmentForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(enrollment_open=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Select Course"
    )

    def __init__(self, student, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        enrolled_courses = student.courses.values_list('id', flat=True)
        pending_courses = EnrollmentRequest.objects.filter(
            student=student,
            status='pending'
        ).values_list('course_id', flat=True)

        self.fields['course'].queryset = Course.objects.filter(
            enrollment_open=True
        ).exclude(
            id__in=enrolled_courses
        ).exclude(
            id__in=pending_courses
        )


class StudentSignupForm(forms.Form):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
    ]

    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') and cleaned.get('password2'):
            if cleaned['password1'] != cleaned['password2']:
                raise forms.ValidationError('Passwords do not match.')
        return cleaned

    def save_pending(self):
        data = self.cleaned_data
        user = User(
            username=data['username'],
            email=data['email'],
            phone=data.get('phone') or '',
            role=data['role'],
            is_active=False,  # pending admin approval
        )
        user.set_password(data['password1'])
        user.save()
        return user

