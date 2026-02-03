# hr/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from .models import HR, HRTimeSlot, HRInterviewBooking, HRInterviewFeedback
from candidate.models import PasswordResetOTP, CandidateProfile
import hashlib
from datetime import timedelta, datetime, date
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.utils.timezone import make_aware

def _auto_update_no_shows_for_hr(hr_user):
    """Mark scheduled interviews as no_show if >10 minutes past start time."""
    from datetime import datetime
    now = datetime.now()
    scheduled = HRInterviewBooking.objects.filter(hr=hr_user, status='scheduled').select_related('time_slot')
    for booking in scheduled:
        interview_end_dt = datetime.combine(booking.time_slot.date, booking.time_slot.end_time)
        minutes_after_end = (now - interview_end_dt).total_seconds() / 60
        # Only mark as no_show if it's more than 10 minutes after the scheduled end time
        if minutes_after_end > 10:
            booking.status = 'no_show'
            booking.save()

def send_email_otp(email, otp, subject, message):
    """Send OTP via email using SMTP"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        print(f"   Attempted to send to: {email}")
        print(f"   Check your SMTP configuration in settings.py and .env file")
        print(f"   Make sure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set correctly")
        return False

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            hr_user = HR.objects.get(email=email, is_active=True)
            
            # Check password
            if hr_user.check_password(password):
                # Store HR info in session
                request.session['hr_id'] = hr_user.id
                request.session['hr_email'] = hr_user.email
                request.session['hr_name'] = hr_user.full_name
                messages.success(request, f'Welcome back, {hr_user.full_name}!')
                return redirect('hr_dashboard')
            else:
                messages.error(request, 'Invalid email or password')
        except HR.DoesNotExist:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'hr/login.html')

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            hr_user = HR.objects.get(email=email, is_active=True)
            
            # Create OTP for password reset
            otp_instance = PasswordResetOTP.create_otp(email)
            
            # Send email with OTP
            subject = 'Password Reset OTP - AI Mock Interview Platform'
            message = f'''Hello {hr_user.full_name}!

You requested a password reset for your HR account.

Your password reset OTP is: {otp_instance.otp}

This OTP will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
AI Mock Interview Platform Team'''
            
            if send_email_otp(email, otp_instance.otp, subject, message):
                messages.success(request, f'Password reset OTP has been sent to {email}')
                return redirect('hr_reset_password')
            else:
                messages.error(request, 'Failed to send OTP. Please try again.')
                
        except HR.DoesNotExist:
            messages.error(request, 'No HR account found with this email address.')
    
    return render(request, 'hr/forgot_password.html')

def reset_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate passwords match
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'hr/reset_password.html')
        
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'hr/reset_password.html')
        
        try:
            # Verify OTP
            otp_instance = PasswordResetOTP.objects.get(
                email=email, 
                otp=otp, 
                is_used=False
            )
            
            # Check if OTP is expired
            if otp_instance.is_expired():
                messages.error(request, 'OTP has expired. Please request a new one.')
                return redirect('hr_forgot_password')
            
            # Update HR password
            hr_user = HR.objects.get(email=email, is_active=True)
            hr_user.set_password(new_password)
            hr_user.save()
            
            # Mark OTP as used
            otp_instance.is_used = True
            otp_instance.save()
            
            messages.success(request, 'Password has been reset successfully! Please login with your new password.')
            return redirect('hr_login')
            
        except PasswordResetOTP.DoesNotExist:
            messages.error(request, 'Invalid OTP. Please check and try again.')
        except HR.DoesNotExist:
            messages.error(request, 'HR account not found.')
    
    return render(request, 'hr/reset_password.html')

def dashboard_view(request):
    # Require HR session
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_name = request.session.get('hr_name', 'HR User')
    
    # Get HR user details
    try:
        hr_user = HR.objects.get(id=request.session['hr_id'])
    except HR.DoesNotExist:
        # Clear invalid session
        request.session.pop('hr_id', None)
        request.session.pop('hr_email', None)
        request.session.pop('hr_name', None)
        return redirect('hr_login')
    
    # Auto-update missed interviews as no_show
    _auto_update_no_shows_for_hr(hr_user)

    # Get current date and time for proper filtering
    from datetime import datetime
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Get updated statistics
    # Count all interviews associated with this HR (any status)
    total_interviews_conducted = HRInterviewBooking.objects.filter(hr=hr_user).count()
    todays_interviews_scheduled = HRInterviewBooking.objects.filter(
        hr=hr_user, 
        time_slot__date=current_date,
        status='scheduled'
    ).count()
    
    # Get all scheduled interviews and filter properly for upcoming ones
    all_scheduled = HRInterviewBooking.objects.filter(
        hr=hr_user,
        status='scheduled'
    ).select_related('time_slot')
    
    # Count truly upcoming interviews (future date OR same date within 10-minute window)
    upcoming_count = 0
    for interview in all_scheduled:
        interview_datetime = datetime.combine(interview.time_slot.date, interview.time_slot.start_time)
        time_diff_minutes = (interview_datetime - now).total_seconds() / 60
        
        if (interview.time_slot.date > current_date or 
            (interview.time_slot.date == current_date and time_diff_minutes > -10)):
            upcoming_count += 1
    
    # Get today's interviews with candidate profiles for join buttons
    todays_interviews = HRInterviewBooking.objects.filter(
        hr=hr_user,
        time_slot__date=date.today(),
        status='scheduled'
    ).select_related('candidate', 'time_slot').order_by('time_slot__start_time')
    
    candidate_ids = [interview.candidate_id for interview in todays_interviews]
    profiles_map = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_ids)}
    
    todays_interviews_data = []
    for interview in todays_interviews:
        todays_interviews_data.append({
            'interview': interview,
            'profile': profiles_map.get(interview.candidate_id)
        })
    
    context = {
        'hr_name': hr_name,
        'hr_user': hr_user,
        'total_interviews_conducted': total_interviews_conducted,
        'todays_interviews_scheduled': todays_interviews_scheduled,
        'upcoming_interviews': upcoming_count,
        'todays_interviews_data': todays_interviews_data,
    }
    
    return render(request, 'hr/dashboard.html', context)

def manage_time_slots_view(request):
    """HR can manage their time slots"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])

    if request.method == 'POST':
        action = request.POST.get('action')
        slot_id = request.POST.get('slot_id')
        if action == 'delete' and slot_id:
            try:
                # Only allow deleting unbooked, managed slots
                slot = HRTimeSlot.objects.get(id=slot_id, hr=hr_user, is_managed=True, is_available=True)
                slot.delete()
                messages.success(request, 'Time slot deleted successfully.')
            except HRTimeSlot.DoesNotExist:
                messages.error(request, 'Time slot not found or cannot be deleted.')
        elif action == 'add':
            # Generate only for next 7 days from today (inclusive)
            start_date = date.today()
            for i in range(7):
                current_date = start_date + timedelta(days=i)
                # Skip Sundays (weekday(): Monday=0, Sunday=6)
                if current_date.weekday() == 6:
                    continue
                day_start_hour = 9
                day_end_hour = 17
                for hour in range(day_start_hour, day_end_hour):
                    for minute in [0, 30]:
                        start_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
                        # Calculate end time properly
                        if minute == 30:
                            next_end_hour = hour + 1
                            next_end_minute = 0
                        else:
                            next_end_hour = hour
                            next_end_minute = 30
                        end_time = datetime.strptime(f"{next_end_hour:02d}:{next_end_minute:02d}", "%H:%M").time()
                        # Use only unique constraint fields in lookup to avoid IntegrityError
                        HRTimeSlot.objects.get_or_create(
                            hr=hr_user,
                            date=current_date,
                            start_time=start_time,
                            defaults={'end_time': end_time, 'is_managed': True}
                        )
            messages.success(request, 'Time slots generated for the next 7 days.')

    # Show only manageable (unbooked) future slots; for today, only times after current time
    from datetime import datetime as _dt
    now_time = _dt.now().time()
    managed_slots = HRTimeSlot.objects.filter(
        hr=hr_user,
        is_managed=True,
        is_available=True
    ).filter(
        Q(date__gt=date.today()) | Q(date=date.today(), start_time__gt=now_time)
    ).order_by('date', 'start_time')

    context = {
        'hr_user': hr_user,
        'managed_slots': managed_slots,
    }
    return render(request, 'hr/manage_time_slots.html', context)


def booked_time_slots_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])
    booked_slots = HRTimeSlot.objects.filter(
        hr=hr_user,
        is_available=False,
        date__gte=date.today()
    ).order_by('date', 'start_time')
    return render(request, 'hr/booked_time_slots.html', {
        'hr_user': hr_user,
        'booked_slots': booked_slots,
    })


def interviews_conducted_list_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])
    bookings_qs = HRInterviewBooking.objects.filter(hr=hr_user).select_related('candidate', 'time_slot').order_by('-created_at')
    candidate_ids = [b.candidate_id for b in bookings_qs]
    profiles_map = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_ids)}
    bookings = []
    from datetime import datetime as _dt
    now = _dt.now()
    for b in bookings_qs:
        profile = profiles_map.get(b.candidate_id)
        if profile and getattr(profile, 'name', None):
            display_name = profile.name
        elif b.candidate.get_full_name():
            display_name = b.candidate.get_full_name()
        else:
            display_name = b.candidate.username
        bookings.append({
            'booking': b,
            'profile': profile,
            'display_name': display_name,
        })
    return render(request, 'hr/interviews_conducted_list.html', {
        'hr_user': hr_user,
        'bookings': bookings,
    })


def todays_interviews_list_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])
    _auto_update_no_shows_for_hr(hr_user)
    today = date.today()
    bookings_qs = HRInterviewBooking.objects.filter(
        hr=hr_user,
        status='scheduled',
        time_slot__date=today
    ).select_related('candidate', 'time_slot')
    candidate_ids = [b.candidate_id for b in bookings_qs]
    profiles_map = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_ids)}
    bookings = []
    for b in bookings_qs:
        bookings.append({
            'booking': b,
            'profile': profiles_map.get(b.candidate_id)
        })
    return render(request, 'hr/todays_interviews_list.html', {
        'hr_user': hr_user,
        'bookings': bookings,
        'today': today,
    })


def upcoming_interviews_list_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])
    _auto_update_no_shows_for_hr(hr_user)
    
    # Get current date and time for proper filtering
    from datetime import datetime
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Get all scheduled interviews
    all_scheduled = HRInterviewBooking.objects.filter(
        hr=hr_user,
        status='scheduled'
    ).select_related('candidate', 'time_slot')
    
    # Filter for truly upcoming interviews (future date OR same date within 10-minute window)
    upcoming_bookings = []
    for booking in all_scheduled:
        interview_datetime = datetime.combine(booking.time_slot.date, booking.time_slot.start_time)
        time_diff_minutes = (interview_datetime - now).total_seconds() / 60
        
        if (booking.time_slot.date > current_date or 
            (booking.time_slot.date == current_date and time_diff_minutes > -10)):
            upcoming_bookings.append(booking)
    
    # Sort by date and time (nearest first)
    upcoming_bookings.sort(key=lambda x: (x.time_slot.date, x.time_slot.start_time))
    
    # Get candidate profiles
    candidate_ids = [b.candidate_id for b in upcoming_bookings]
    profiles_map = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_ids)}
    
    bookings = []
    for b in upcoming_bookings:
        bookings.append({
            'booking': b,
            'profile': profiles_map.get(b.candidate_id)
        })
    
    return render(request, 'hr/upcoming_interviews_list.html', {
        'hr_user': hr_user,
        'bookings': bookings,
        'current_date': current_date,
        'current_time': current_time,
    })


def manage_interviews_view(request):
    """HR can view and manage all scheduled interviews"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    _auto_update_no_shows_for_hr(hr_user)
    
    # Get current date and time for filtering
    from datetime import datetime
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Get all interviews for this HR
    all_interviews = HRInterviewBooking.objects.filter(
        hr=hr_user
    ).select_related('candidate', 'time_slot')
    
    # Get candidate profiles for display
    candidate_ids = [interview.candidate_id for interview in all_interviews]
    profiles_map = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_ids)}
    
    # Separate interviews into upcoming and past
    upcoming_interviews = []
    past_interviews = []
    
    for interview in all_interviews:
        interview_datetime = datetime.combine(interview.time_slot.date, interview.time_slot.start_time)
        
        # Calculate time difference in minutes
        time_diff_minutes = (interview_datetime - now).total_seconds() / 60
        
        # Compute flags
        profile = profiles_map.get(interview.candidate_id)
        display_name = None
        if profile and getattr(profile, 'name', None):
            display_name = profile.name
        elif interview.candidate.get_full_name():
            display_name = interview.candidate.get_full_name()
        else:
            display_name = interview.candidate.username
        
        # Allow manual completion only 5 minutes after scheduled start
        allow_mark_complete = False
        try:
            allow_mark_complete = now >= (datetime.combine(interview.time_slot.date, interview.time_slot.start_time) + timedelta(minutes=5)) and interview.status == 'scheduled'
        except Exception:
            allow_mark_complete = interview.status == 'scheduled'
        
        # Check feedback existence using the reverse relationship
        has_feedback = hasattr(interview, 'feedback')
        
        item = {
            'interview': interview,
            'profile': profile,
            'datetime': interview_datetime,
            'display_name': display_name,
            'allow_mark_complete': allow_mark_complete,
            'has_feedback': has_feedback,
        }
        
        # Check if interview is in the future OR within the 10-minute joining window
        if (interview.time_slot.date > current_date or 
            (interview.time_slot.date == current_date and time_diff_minutes > -10)):
            # This is an upcoming interview (future OR within 10 minutes after start time)
            upcoming_interviews.append(item)
        else:
            # This is a past interview (more than 10 minutes after start time)
            past_interviews.append(item)
    
    # Sort upcoming interviews by nearest time first (ascending)
    upcoming_interviews.sort(key=lambda x: x['datetime'])
    
    # Sort past interviews by most recent first (descending)
    past_interviews.sort(key=lambda x: x['datetime'], reverse=True)
    
    context = {
        'hr_user': hr_user,
        'upcoming_interviews': upcoming_interviews,
        'past_interviews': past_interviews,
        'current_date': current_date,
        'current_time': current_time,
    }
    
    return render(request, 'hr/manage_interviews.html', context)

def join_interview_view(request, booking_id):
    """HR can join a scheduled interview"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    
    try:
        booking = HRInterviewBooking.objects.get(
            id=booking_id,
            hr=hr_user,
            status='scheduled'
        )
        
        # Check if it's time for the interview (within 10 minutes after start time)
        if not booking.is_meeting_ready:
            messages.error(request, 'Interview is not ready yet. You can join within 10 minutes after the scheduled start time.')
            return redirect('hr_manage_interviews')
        
        # Get candidate profile
        try:
            profile = CandidateProfile.objects.get(user=booking.candidate)
        except CandidateProfile.DoesNotExist:
            profile = None
        
        context = {
            'hr_user': hr_user,
            'booking': booking,
            'profile': profile,
        }
        
        return render(request, 'hr/join_interview.html', context)
        
    except HRInterviewBooking.DoesNotExist:
        messages.error(request, 'Interview not found or you do not have permission to access it.')
        return redirect('hr_manage_interviews')

def complete_interview_view(request, booking_id):
    """HR can manually mark an interview as completed"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    
    if request.method == 'POST':
        try:
            booking = HRInterviewBooking.objects.get(
                id=booking_id,
                hr=hr_user,
                status='scheduled'
            )
            
            notes = request.POST.get('notes', '')
            booking.notes = notes
            
            # Always mark as completed when HR manually completes
            booking.status = 'completed'
            
            # Set attendance tracking fields for manual completion
            booking.both_attended = True
            booking.actual_duration_minutes = 30  # Assume 30 minutes for manual completion
            
            # Set join times if not already set
            if not booking.hr_joined_at:
                booking.hr_joined_at = timezone.now() - timedelta(minutes=30)
            if not booking.candidate_joined_at:
                booking.candidate_joined_at = timezone.now() - timedelta(minutes=25)
            
            booking.save()
            messages.success(request, 'Interview marked as completed successfully. Feedback is now available.')
            return redirect('hr_manage_interviews')
            
        except HRInterviewBooking.DoesNotExist:
            messages.error(request, 'Interview not found.')
    
    return redirect('hr_manage_interviews')

def track_attendance_view(request, booking_id):
    """API endpoint to track meeting attendance"""
    if 'hr_id' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    
    try:
        booking = HRInterviewBooking.objects.get(
            id=booking_id,
            hr=hr_user
        )
        
        action = request.POST.get('action')
        
        if action == 'hr_joined':
            booking.mark_hr_joined()
            return JsonResponse({'status': 'success', 'message': 'HR attendance recorded'})
        elif action == 'hr_left':
            booking.mark_hr_left()
            return JsonResponse({'status': 'success', 'message': 'HR departure recorded'})
        elif action == 'candidate_joined':
            booking.mark_candidate_joined()
            return JsonResponse({'status': 'success', 'message': 'Candidate attendance recorded'})
        elif action == 'candidate_left':
            booking.mark_candidate_left()
            return JsonResponse({'status': 'success', 'message': 'Candidate departure recorded'})
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
    except HRInterviewBooking.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def view_candidates_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])
    # Candidates who booked with this HR (any status)
    bookings = HRInterviewBooking.objects.filter(hr=hr_user).select_related('candidate', 'time_slot').order_by('-created_at')
    # Group by candidate
    candidate_map = {}
    for b in bookings:
        candidate_map.setdefault(b.candidate_id, {
            'user': b.candidate,
            'bookings': []
        })
        candidate_map[b.candidate_id]['bookings'].append(b)
    # Augment with profiles
    profiles = {p.user_id: p for p in CandidateProfile.objects.filter(user_id__in=candidate_map.keys())}
    return render(request, 'hr/candidates_list.html', {
        'hr_user': hr_user,
        'candidates': candidate_map,
        'profiles': profiles,
    })

def logout_view(request):
    # Clear HR session
    request.session.pop('hr_id', None)
    request.session.pop('hr_email', None)
    request.session.pop('hr_name', None)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('hr_login')

def analytics_view(request):
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    hr_user = HR.objects.get(id=request.session['hr_id'])

    # Parse month/year from query params; default to current month
    today = date.today()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year

    # Compute date range for the month
    from calendar import monthrange
    start_date = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    # Base queryset for this HR and month
    month_bookings = HRInterviewBooking.objects.filter(
        hr=hr_user,
        time_slot__date__gte=start_date,
        time_slot__date__lte=end_date,
    )

    total_interviews = month_bookings.count()
    completed_interviews = month_bookings.filter(status='completed').count()
    scheduled_interviews = month_bookings.filter(status='scheduled').count()
    cancelled_interviews = month_bookings.filter(status='cancelled').count()
    no_show_interviews = month_bookings.filter(status='no_show').count()

    context = {
        'hr_user': hr_user,
        'month': month,
        'year': year,
        'start_date': start_date,
        'end_date': end_date,
        'total_interviews': total_interviews,
        'completed_interviews': completed_interviews,
        'scheduled_interviews': scheduled_interviews,
        'cancelled_interviews': cancelled_interviews,
        'no_show_interviews': no_show_interviews,
        'bookings': month_bookings.select_related('candidate', 'time_slot').order_by('time_slot__date', 'time_slot__start_time'),
    }

    return render(request, 'hr/analytics.html', context)

@login_required
def book_hr_interview(request, hr_id, slot_id):
    """Book an HR interview slot"""
    try:
        hr = HR.objects.get(id=hr_id, is_active=True)
        time_slot = HRTimeSlot.objects.get(id=slot_id, hr=hr, is_available=True)
        profile = CandidateProfile.objects.get(user=request.user)
        
        # Prevent booking past slots (same day past start or any past date)
        from datetime import datetime as _dt
        now = _dt.now()
        slot_dt = _dt.combine(time_slot.date, time_slot.start_time)
        if slot_dt <= now:
            messages.error(request, 'This time slot has already passed. Please choose a future slot.')
            return redirect('hr_time_slots', hr_id=hr.id)
        
        # Create the booking
        booking = HRInterviewBooking.objects.create(
            candidate=request.user,
            hr=hr,
            time_slot=time_slot,
            designation=profile.designation
        )
        
        messages.success(request, f'Interview booked successfully with {hr.full_name}!')
        return redirect('hr_booking_confirmation', booking_id=booking.id)
        
    except (HR.DoesNotExist, HRTimeSlot.DoesNotExist):
        messages.error(request, 'Invalid HR or time slot.')
        return redirect('hr_interview_booking')

def give_feedback_view(request, booking_id):
    """HR can give feedback for a completed interview"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    
    try:
        booking = HRInterviewBooking.objects.get(
            id=booking_id,
            hr=hr_user
        )
        
        # Allow feedback for any completed interview; block otherwise
        if booking.status != 'completed':
            messages.error(request, 'Interview must be marked as completed before giving feedback.')
            return redirect('hr_manage_interviews')
        
        # Check if feedback already exists
        try:
            existing_feedback = HRInterviewFeedback.objects.get(booking=booking)
            messages.info(request, 'Feedback already provided for this interview.')
            return redirect('hr_manage_interviews')
        except HRInterviewFeedback.DoesNotExist:
            pass
        
        if request.method == 'POST':
            # Process feedback form
            relevance_clarity = int(request.POST.get('relevance_clarity', 1))
            technical_knowledge = int(request.POST.get('technical_knowledge', 1))
            communication_skills = int(request.POST.get('communication_skills', 1))
            problem_solving = int(request.POST.get('problem_solving', 1))
            experience_examples = int(request.POST.get('experience_examples', 1))
            
            # Process strengths and improvements (comma-separated)
            strengths_text = request.POST.get('strengths', '')
            improvements_text = request.POST.get('areas_for_improvement', '')
            
            strengths = [s.strip() for s in strengths_text.split(',') if s.strip()]
            areas_for_improvement = [s.strip() for s in improvements_text.split(',') if s.strip()]
            
            detailed_feedback = request.POST.get('detailed_feedback', '')
            recommendation = request.POST.get('recommendation', '')
            additional_notes = request.POST.get('additional_notes', '')
            
            # Create feedback
            feedback = HRInterviewFeedback.objects.create(
                booking=booking,
                hr=hr_user,
                candidate=booking.candidate,
                relevance_clarity=relevance_clarity,
                technical_knowledge=technical_knowledge,
                communication_skills=communication_skills,
                problem_solving=problem_solving,
                experience_examples=experience_examples,
                strengths=strengths,
                areas_for_improvement=areas_for_improvement,
                detailed_feedback=detailed_feedback,
                recommendation=recommendation,
                additional_notes=additional_notes
            )
            
            messages.success(request, 'Feedback submitted successfully!')
            return redirect('hr_manage_interviews')
        
        # Get candidate profile for context
        try:
            profile = CandidateProfile.objects.get(user=booking.candidate)
        except CandidateProfile.DoesNotExist:
            profile = None
        
        context = {
            'hr_user': hr_user,
            'booking': booking,
            'profile': profile,
        }
        
        return render(request, 'hr/give_feedback.html', context)
        
    except HRInterviewBooking.DoesNotExist:
        messages.error(request, 'Interview not found or you do not have permission to access it.')
        return redirect('hr_manage_interviews')

def view_feedback_view(request, booking_id):
    """HR can view/edit their feedback for an interview"""
    if 'hr_id' not in request.session:
        return redirect('hr_login')
    
    hr_user = HR.objects.get(id=request.session['hr_id'])
    
    try:
        booking = HRInterviewBooking.objects.get(
            id=booking_id,
            hr=hr_user,
            status='completed'
        )
        
        try:
            feedback = HRInterviewFeedback.objects.get(booking=booking)
        except HRInterviewFeedback.DoesNotExist:
            messages.error(request, 'No feedback found for this interview.')
            return redirect('hr_manage_interviews')
        
        # Get candidate profile and replies
        try:
            profile = CandidateProfile.objects.get(user=booking.candidate)
        except CandidateProfile.DoesNotExist:
            profile = None
        
        replies = feedback.replies.all()
        
        context = {
            'hr_user': hr_user,
            'booking': booking,
            'profile': profile,
            'feedback': feedback,
            'replies': replies,
        }
        
        return render(request, 'hr/view_feedback.html', context)
        
    except HRInterviewBooking.DoesNotExist:
        messages.error(request, 'Interview not found or you do not have permission to access it.')
        return redirect('hr_manage_interviews')
