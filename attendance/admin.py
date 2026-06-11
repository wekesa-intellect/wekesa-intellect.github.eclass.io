from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, AttendanceSession, AttendanceRecord, AuditLog

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'phone')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)
admin.site.register(AuditLog)