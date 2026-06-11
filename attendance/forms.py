from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import AttendanceSession, Course, EnrollmentRequest

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