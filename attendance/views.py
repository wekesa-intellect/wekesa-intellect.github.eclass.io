from .models import User, Course, AttendanceSession, AttendanceRecord, AuditLog, EnrollmentRequest
from .forms import LoginForm, SessionForm, CodeForm, CourseEnrollmentForm, StudentSignupForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import datetime

# Import export utilities
from .export_utils import ReportExporter


# Helper for audit logging
def log_action(user, action, request):
    ip = request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(user=user, action=action, ip=ip)


# ---------- Authentication Views ----------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_action(user, 'Logged in', request)
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'attendance/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'Logged out', request)
    logout(request)
    return redirect('login')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save_pending()
            messages.success(
                request,
                'Your request has been created. Wait for admin approval before logging in.'
            )
            return redirect('login')
    else:
        form = StudentSignupForm(initial={'role': 'student'})

    return render(request, 'attendance/signup.html', {'form': form})


# ---------- Dashboard (Role-based landing) ----------
@login_required
def dashboard(request):
    user = request.user
    if user.role == 'lecturer':
        active = AttendanceSession.objects.filter(lecturer=user, is_active=True)
        recent = AttendanceSession.objects.filter(lecturer=user).order_by('-start_time')[:5]
        return render(request, 'attendance/lecturer_dashboard.html', {'active_sessions': active, 'recent_sessions': recent})
    elif user.role == 'student':
        data = []
        for course in user.courses.all():
            total = AttendanceSession.objects.filter(course=course).count()
            attended = AttendanceRecord.objects.filter(student=user, session__course=course).count()
            percent = (attended / total * 100) if total else 0
            data.append({
                'course': course,
                'attended': attended,
                'total': total,
                'percent': round(percent, 2),
                'status': 'Compliant' if percent >= 80 else 'Below 80%',
            })
        return render(request, 'attendance/student_dashboard.html', {'data': data})
    else:
        total_students = User.objects.filter(role='student').count()
        total_lecturers = User.objects.filter(role='lecturer').count()
        total_courses = Course.objects.count()
        today_sessions = AttendanceSession.objects.filter(date=timezone.now().date()).count()
        pending_users = User.objects.filter(is_active=False).order_by('-date_joined')
        return render(request, 'attendance/admin_dashboard.html', {
            'total_students': total_students,
            'total_lecturers': total_lecturers,
            'total_courses': total_courses,
            'today_sessions': today_sessions,
            'pending_users': pending_users,
        })



# ---------- Lecturer - Create & Manage Sessions ----------
@login_required
def create_session(request):
    if request.user.role != 'lecturer':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    if request.method == 'POST':
        form = SessionForm(request.user, request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.lecturer = request.user

            if not session.require_location:
                session.latitude = None
                session.longitude = None
            else:
                if not session.latitude or not session.longitude:
                    messages.error(request, 'Please set the lecture hall location')
                    return render(request, 'attendance/create_session.html', {'form': form})

            session.save()
            log_action(request.user, f'Created session {session.code}', request)
            messages.success(request, f'Session created! Code: {session.code}')
            return redirect('session_detail', session.id)
    else:
        form = SessionForm(request.user)

    return render(request, 'attendance/create_session.html', {'form': form})


@login_required
def session_detail(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id, lecturer=request.user)
    if request.method == 'POST' and 'close' in request.POST:
        session.close()
        log_action(request.user, f'Closed session {session.code}', request)
        messages.success(request, 'Session closed')
        return redirect('session_detail', session.id)
    return render(request, 'attendance/session_detail.html', {'session': session, 'records': session.records.all()})


# ---------- Lecturer Reports ----------
@login_required
def lecturer_reports(request):
    if request.user.role != 'lecturer':
        return redirect('dashboard')
    courses = Course.objects.filter(lecturer=request.user)
    report = []
    for course in courses:
        sessions = AttendanceSession.objects.filter(course=course)
        total = sessions.count()
        students_data = []
        for student in course.students.all():
            attended = AttendanceRecord.objects.filter(session__course=course, student=student).count()
            percent = (attended / total * 100) if total else 0
            students_data.append({
                'student': student,
                'attended': attended,
                'percent': round(percent, 2),
                'compliant': percent >= 80,
            })
        report.append({'course': course, 'total_sessions': total, 'students': students_data})
    return render(request, 'attendance/lecturer_reports.html', {'report': report})


# ---------- Export Views ----------
@login_required
def export_course_attendance_excel(request, course_id):
    """Export course attendance to Excel"""
    if request.user.role not in ['lecturer', 'admin']:
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    course = get_object_or_404(Course, id=course_id)

    # Check permissions
    if request.user.role == 'lecturer' and course.lecturer != request.user:
        messages.error(request, 'You can only export your own courses')
        return redirect('dashboard')

    # Prepare data
    total_sessions = AttendanceSession.objects.filter(course=course).count()
    students_data = []
    total_attendance = 0

    for student in course.students.all():
        attended = AttendanceRecord.objects.filter(session__course=course, student=student).count()
        percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
        total_attendance += percentage
        students_data.append({
            'name': student.username,
            'email': student.email,
            'attended': attended,
            'total': total_sessions,
            'percentage': round(percentage, 2),
        })

    course_data = {
        'total_students': course.students.count(),
        'total_sessions': total_sessions,
        'average_attendance': round(total_attendance / course.students.count(), 2) if course.students.count() > 0 else 0,
        'below_80_count': sum(1 for s in students_data if s['percentage'] < 80),
        'students': students_data,
    }

    log_action(request.user, f'Exported Excel report for {course.code}', request)
    return ReportExporter.export_attendance_to_excel(course_data, course.code)


@login_required
def export_course_attendance_pdf(request, course_id):
    """Export course attendance to PDF"""
    if request.user.role not in ['lecturer', 'admin']:
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    course = get_object_or_404(Course, id=course_id)

    # Check permissions
    if request.user.role == 'lecturer' and course.lecturer != request.user:
        messages.error(request, 'You can only export your own courses')
        return redirect('dashboard')

    # Prepare data
    total_sessions = AttendanceSession.objects.filter(course=course).count()
    students_data = []
    total_attendance = 0

    for student in course.students.all():
        attended = AttendanceRecord.objects.filter(session__course=course, student=student).count()
        percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
        total_attendance += percentage
        students_data.append({
            'name': student.username,
            'email': student.email,
            'attended': attended,
            'total': total_sessions,
            'percentage': round(percentage, 2),
        })

    course_data = {
        'total_students': course.students.count(),
        'total_sessions': total_sessions,
        'average_attendance': round(total_attendance / course.students.count(), 2) if course.students.count() > 0 else 0,
        'below_80_count': sum(1 for s in students_data if s['percentage'] < 80),
        'students': students_data,
    }

    log_action(request.user, f'Exported PDF report for {course.code}', request)
    return ReportExporter.export_attendance_to_pdf(course_data, course.code)


# ---------- Student - Mark Attendance & History ----------
@login_required
def mark_attendance(request):
    if request.user.role != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].upper()

            try:
                session = AttendanceSession.objects.get(code=code, is_active=True)
            except AttendanceSession.DoesNotExist:
                messages.error(request, 'Invalid or expired code')
                return redirect('mark_attendance')

            if not session.course.students.filter(id=request.user.id).exists():
                messages.error(request, 'You are not enrolled in this course')
                return redirect('mark_attendance')

            if AttendanceRecord.objects.filter(session=session, student=request.user).exists():
                messages.error(request, 'Already marked for this session')
                return redirect('mark_attendance')

            deadline = session.start_time + datetime.timedelta(minutes=session.duration_minutes)
            if timezone.now() > deadline:
                session.is_active = False
                session.save()
                messages.error(request, 'Attendance window has expired')
                return redirect('mark_attendance')

            verification_passed = False
            student_lat = None
            student_lng = None

            if session.session_type == 'online':
                verification_passed = True
            elif session.session_type == 'physical':
                if session.require_location:
                    student_lat = request.POST.get('latitude')
                    student_lng = request.POST.get('longitude')

                    if not student_lat or not student_lng:
                        messages.error(request, 'Location verification required. Please enable location services.')
                        return render(request, 'attendance/mark_attendance.html', {
                            'form': form,
                            'require_location': True,
                            'session': session,
                        })

                    if session.is_within_radius(float(student_lat), float(student_lng)):
                        verification_passed = True
                    else:
                        messages.error(request, f'You must be within {session.allowed_radius} meters of the lecture hall')
                        return redirect('mark_attendance')
                else:
                    verification_passed = True

            if verification_passed:
                AttendanceRecord.objects.create(
                    session=session,
                    student=request.user,
                    ip=request.META.get('REMOTE_ADDR'),
                    latitude=student_lat,
                    longitude=student_lng,
                )
                log_action(request.user, f'Marked attendance {session.code}', request)
                messages.success(request, 'Attendance recorded successfully!')
                return redirect('student_history')

    else:
        form = CodeForm()

    return render(request, 'attendance/mark_attendance.html', {'form': form})


@login_required
def student_history(request):
    records = AttendanceRecord.objects.filter(student=request.user).select_related('session__course').order_by('-timestamp')
    return render(request, 'attendance/student_history.html', {'records': records})


# ---------- Admin - Faculty Reports ----------
@login_required
def admin_reports(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    courses = Course.objects.all()
    report = []
    for course in courses:
        total = AttendanceSession.objects.filter(course=course).count()
        if total == 0:
            continue
        below = 0
        for student in course.students.all():
            attended = AttendanceRecord.objects.filter(session__course=course, student=student).count()
            if (attended / total * 100) < 80:
                below += 1
        report.append({'course': course, 'total_sessions': total, 'enrolled': course.students.count(), 'below_80': below})
    return render(request, 'attendance/admin_reports.html', {'report': report})


# ---------- Student Enrollment Views ----------
@login_required
def browse_courses(request):
    if request.user.role != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    enrolled_courses = request.user.courses.all()
    pending_requests = EnrollmentRequest.objects.filter(student=request.user, status='pending')
    pending_course_ids = pending_requests.values_list('course_id', flat=True)

    available_courses = Course.objects.filter(enrollment_open=True).exclude(id__in=enrolled_courses).exclude(id__in=pending_course_ids)

    if request.method == 'POST':
        form = CourseEnrollmentForm(request.user, request.POST)
        if form.is_valid():
            course = form.cleaned_data['course']

            if course.is_full and course.capacity > 0:
                messages.error(request, f'{course.code} is already full!')
                return redirect('browse_courses')

            enrollment_request = EnrollmentRequest.objects.create(student=request.user, course=course)

            if course.auto_approve:
                enrollment_request.approve(request.user)
                messages.success(request, f'Successfully enrolled in {course.code}!')
                log_action(request.user, f'Enrolled in course {course.code}', request)
            else:
                messages.info(request, f'Enrollment request sent for {course.code}. Waiting for approval.')
                log_action(request.user, f'Requested enrollment for {course.code}', request)

            return redirect('my_courses')
    else:
        form = CourseEnrollmentForm(request.user)

    context = {
        'enrolled_courses': enrolled_courses,
        'pending_requests': pending_requests,
        'available_courses': available_courses,
        'form': form,
    }
    return render(request, 'attendance/browse_courses.html', context)


@login_required
def my_courses(request):
    if request.user.role != 'student':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    enrolled_courses = request.user.courses.all()
    pending_requests = EnrollmentRequest.objects.filter(student=request.user, status='pending')
    rejected_requests = EnrollmentRequest.objects.filter(student=request.user, status='rejected')

    course_attendance = []
    for course in enrolled_courses:
        total_sessions = AttendanceSession.objects.filter(course=course).count()
        attended_sessions = AttendanceRecord.objects.filter(student=request.user, session__course=course).count()
        percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0

        course_attendance.append({
            'course': course,
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'percentage': round(percentage, 2),
            'compliant': percentage >= 80,
        })

    context = {
        'enrolled_courses': course_attendance,
        'pending_requests': pending_requests,
        'rejected_requests': rejected_requests,
    }
    return render(request, 'attendance/my_courses.html', context)


@login_required
def manage_enrollments(request):
    if request.user.role != 'lecturer':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    pending_requests = EnrollmentRequest.objects.filter(course__lecturer=request.user, status='pending').select_related('student', 'course')
    processed_requests = EnrollmentRequest.objects.filter(course__lecturer=request.user).exclude(status='pending').select_related('student', 'course')[:20]

    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        try:
            enrollment_request = EnrollmentRequest.objects.get(id=request_id, course__lecturer=request.user)

            if action == 'approve':
                if enrollment_request.course.is_full:
                    messages.error(request, f'Cannot approve - {enrollment_request.course.code} is full!')
                else:
                    enrollment_request.approve(request.user)
                    messages.success(request, f'Approved enrollment for {enrollment_request.student.username}')
                    log_action(request.user, f'Approved enrollment for {enrollment_request.student.username}', request)
            elif action == 'reject':
                enrollment_request.reject(request.user, notes)
                messages.warning(request, f'Rejected enrollment for {enrollment_request.student.username}')
                log_action(request.user, f'Rejected enrollment for {enrollment_request.student.username}', request)

            return redirect('manage_enrollments')
        except EnrollmentRequest.DoesNotExist:
            messages.error(request, 'Invalid enrollment request')

    context = {
        'pending_requests': pending_requests,
        'processed_requests': processed_requests,
    }
    return render(request, 'attendance/manage_enrollments.html', context)


@login_required
def all_enrollments(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    total_requests = EnrollmentRequest.objects.count()
    pending_count = EnrollmentRequest.objects.filter(status='pending').count()
    approved_count = EnrollmentRequest.objects.filter(status='approved').count()
    rejected_count = EnrollmentRequest.objects.filter(status='rejected').count()

    status_filter = request.GET.get('status', '')
    if status_filter:
        enrollment_requests = EnrollmentRequest.objects.filter(status=status_filter).select_related('student', 'course', 'processed_by')
    else:
        enrollment_requests = EnrollmentRequest.objects.all().select_related('student', 'course', 'processed_by')

    course_stats = []
    for course in Course.objects.all():
        course_stats.append({
            'course': course,
            'enrolled': course.students.count(),
            'capacity': course.capacity,
            'pending': EnrollmentRequest.objects.filter(course=course, status='pending').count(),
            'requests': EnrollmentRequest.objects.filter(course=course).count(),
        })

    context = {
        'enrollment_requests': enrollment_requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'course_stats': course_stats,
        'current_filter': status_filter,
    }
    return render(request, 'attendance/all_enrollments.html', context)


@login_required
def course_settings(request, course_id):
    if request.user.role != 'lecturer':
        messages.error(request, 'Access denied')
        return redirect('dashboard')

    course = get_object_or_404(Course, id=course_id, lecturer=request.user)

    if request.method == 'POST':
        course.enrollment_open = request.POST.get('enrollment_open') == 'on'
        course.auto_approve = request.POST.get('auto_approve') == 'on'
        course.capacity = int(request.POST.get('capacity', 0))
        course.description = request.POST.get('description', '')
        course.save()

        messages.success(request, f'Course settings updated for {course.code}')
        log_action(request.user, f'Updated settings for course {course.code}', request)
        return redirect('course_settings', course_id=course.id)

    context = {'course': course}
    return render(request, 'attendance/course_settings.html', context)


# ---------- Home View ----------
def home(request):
    return redirect('login')

