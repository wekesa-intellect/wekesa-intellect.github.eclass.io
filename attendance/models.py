from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.utils import timezone

# ---------- Module 1: Authentication & User Management ----------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('admin', 'Faculty Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


# ---------- Module 2: Course & Enrollment ----------
class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    lecturer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'lecturer'})
    students = models.ManyToManyField(User, related_name='courses', limit_choices_to={'role': 'student'})
    
    # Enrollment management
    enrollment_open = models.BooleanField(default=True)
    auto_approve = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    
    @property
    def available_seats(self):
        if self.capacity == 0:
            return 999
        return max(0, self.capacity - self.students.count())
    
    @property
    def is_full(self):
        if self.capacity == 0:
            return False
        return self.students.count() >= self.capacity
    
    def __str__(self):
        return f"{self.code} - {self.name}"


# ---------- Enrollment Request Model ----------
class EnrollmentRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='enrollment_requests')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollment_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_enrollments')
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-requested_at']
    
    def approve(self, processor):
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.processed_by = processor
        self.save()
        self.course.students.add(self.student)
    
    def reject(self, processor, notes=''):
        self.status = 'rejected'
        self.processed_at = timezone.now()
        self.processed_by = processor
        self.notes = notes
        self.save()
    
    def __str__(self):
        return f"{self.student.username} -> {self.course.code} ({self.status})"


# ---------- Module 3: Attendance Session (Simplified Hybrid) ----------
class AttendanceSession(models.Model):
    SESSION_TYPE_CHOICES = (
        ('physical', '🏢 Physical (In-Person with Location)'),
        ('online', '💻 Online (Virtual - Code Only)'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    
    # Session type
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='physical')
    
    # Physical class fields (only used when session_type = 'physical')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    allowed_radius = models.PositiveIntegerField(default=100, help_text="Allowed radius in meters")
    require_location = models.BooleanField(default=False, help_text="Require GPS verification for physical classes")
    
    # Online class fields (only used when session_type = 'online')
    meeting_link = models.URLField(blank=True, help_text="Optional: Google Meet/Zoom/Teams link")
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)
    
    def close(self):
        self.is_active = False
        self.end_time = timezone.now()
        self.save()
    
    def is_within_radius(self, student_lat, student_lng):
        """Check if student is within allowed radius (for physical classes)"""
        if not self.latitude or not self.longitude:
            return True
        
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000  # Earth's radius in meters
        
        lat1 = radians(float(self.latitude))
        lat2 = radians(float(student_lat))
        delta_lat = radians(float(student_lat) - float(self.latitude))
        delta_lng = radians(float(student_lng) - float(self.longitude))
        
        a = sin(delta_lat/2)**2 + cos(lat1) * cos(lat2) * sin(delta_lng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return distance <= self.allowed_radius
    
    def __str__(self):
        return f"{self.course.code} - {self.date} ({self.get_session_type_display()})"


# ---------- Module 4: Attendance Record ----------
class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    
    # For physical classes - store location data
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        unique_together = ('session', 'student')
    
    def __str__(self):
        return f"{self.student.username} - {self.session.code}"


# ---------- Module 5: Audit Log ----------
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user} - {self.action}"