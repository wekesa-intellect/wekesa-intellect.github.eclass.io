from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),

    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Lecturer URLs
    path('session/create/', views.create_session, name='create_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('lecturer/reports/', views.lecturer_reports, name='lecturer_reports'),
    path('lecturer/enrollments/', views.manage_enrollments, name='manage_enrollments'),
    path('course/<int:course_id>/settings/', views.course_settings, name='course_settings'),
    
    # Export URLs
    path('export/course/<int:course_id>/excel/', views.export_course_attendance_excel, name='export_course_excel'),
    path('export/course/<int:course_id>/pdf/', views.export_course_attendance_pdf, name='export_course_pdf'),
    
    # Student URLs
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('history/', views.student_history, name='student_history'),
    path('courses/browse/', views.browse_courses, name='browse_courses'),
    path('courses/my/', views.my_courses, name='my_courses'),
    
    # Admin URLs (Custom admin views - NOT Django admin)
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/enrollments/', views.all_enrollments, name='all_enrollments'),
]