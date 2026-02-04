from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

import os
from datetime import datetime

from pyresparser import ResumeParser

from ai_interview_platform.utils.question_generator import generate_questions
from ai_interview_platform.utils.evaluator import evaluate_answer
from ai_interview_platform.utils.email_service import send_brevo_email

from .forms import (
    UserRegisterForm,
    ResumeUploadForm,
    DesignationForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    EmailConfirmationForm,
)
from .models import (
    CandidateProfile,
    PasswordResetOTP,
    EmailConfirmationOTP,
    InterviewRecord,
)
from hr.models import HR, HRTimeSlot, HRInterviewBooking, HRInterviewFeedback, CandidateFeedbackReply

def send_email_otp(email, otp, subject, message):
    
    """Send OTP via email using Brevo API"""
    try:
        return send_brevo_email(
            email,
            subject,
            f"<p>{message}</p>"
        )
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        print(f"   Attempted to send to: {email}")
        return False
   

def email_confirmation_view(request):
    """Handle email confirmation OTP request during registration"""
    if request.method == 'POST':
        form = EmailConfirmationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'This email is already registered.')
                return render(request, 'candidate/email_confirmation.html', {'form': form})
            
            # Create OTP
            otp_instance = EmailConfirmationOTP.create_otp(email)
            
            # Send email with OTP
            subject = 'Email Confirmation OTP - AI Mock Interview Platform'
            message = f'''Hello!

Thank you for registering with AI Mock Interview Platform.

Your email confirmation OTP is: {otp_instance.otp}

This OTP will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
AI Mock Interview Platform Team'''
            
            if send_email_otp(email, otp_instance.otp, subject, message):
                messages.success(request, f'OTP has been sent to {email}')
                # Store email in session for registration
                request.session['registration_email'] = email
                return redirect('candidate_register')
            else:
                messages.error(request, 'Failed to send OTP. Please try again.')
    else:
        form = EmailConfirmationForm()
    
    return render(request, 'candidate/email_confirmation.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            email_otp = form.cleaned_data['email_otp']
            
            # Verify email OTP
            try:
                otp_instance = EmailConfirmationOTP.objects.get(
                    email=email, 
                    otp=email_otp, 
                    is_used=False
                )
                
                # Check if OTP is expired
                if otp_instance.is_expired():
                    messages.error(request, 'Email confirmation OTP has expired. Please request a new one.')
                    return redirect('email_confirmation')
                
                # Mark OTP as used
                otp_instance.is_used = True
                otp_instance.save()
                
            except EmailConfirmationOTP.DoesNotExist:
                messages.error(request, 'Invalid email confirmation OTP. Please check and try again.')
                return render(request, 'candidate/register.html', {'form': form})
            
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=form.cleaned_data['password']
            )
            
            # Create candidate profile
            profile = CandidateProfile.objects.create(
                user=user,
                name=form.cleaned_data['name'],
                dob=form.cleaned_data['dob']
            )
            
            # Clear session
            request.session.pop('registration_email', None)
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('candidate_login')
    else:
        # Pre-fill email if available in session
        initial_data = {}
        if 'registration_email' in request.session:
            initial_data['email'] = request.session['registration_email']
        form = UserRegisterForm(initial=initial_data)
    
    return render(request, 'candidate/register.html', {'form': form})

def login_view(request):
    # Collapse any queued messages to a single latest message to avoid duplicate banners after redirects
    storage = messages.get_messages(request)
    last_message = None
    for m in storage:
        last_message = m
    if last_message:
        messages.add_message(request, last_message.level, last_message.message)

    error_message = None
    if request.method == 'POST':
        email = request.POST.get('email')  # Fixed: use 'email' instead of 'username'
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('candidate_dashboard')
        else:
            error_message = "Invalid email or password"
    
    return render(request, 'candidate/login.html', {'error': error_message})

def logout_view(request):
    logout(request)
    return redirect('candidate_login')

def forgot_password_view(request):
    """Handle forgot password request"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Create OTP
                otp_instance = PasswordResetOTP.create_otp(email)
                
                # Send email with OTP
                subject = 'Password Reset OTP - AI Mock Interview Platform'
                message = f'''Hello!

You have requested a password reset for your AI Mock Interview Platform account.

Your password reset OTP is: {otp_instance.otp}

This OTP will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
AI Mock Interview Platform Team'''
                
                if send_email_otp(email, otp_instance.otp, subject, message):
                    messages.success(request, f'OTP has been sent to {email}')
                    return redirect('password_reset_confirm')
                else:
                    messages.error(request, 'Failed to send OTP. Please try again.')
                    
            except User.DoesNotExist:
                messages.error(request, 'No user found with this email address.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'candidate/forgot_password.html', {'form': form})

def password_reset_confirm_view(request):
    """Handle OTP verification and password reset"""
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            new_password = form.cleaned_data['new_password']
            
            try:
                otp_instance = PasswordResetOTP.objects.get(
                    otp=otp, 
                    is_used=False
                )
                
                # Check if OTP is expired
                if otp_instance.is_expired():
                    messages.error(request, 'OTP has expired. Please request a new one.')
                    return redirect('forgot_password')
                
                # Find user by email
                try:
                    user = User.objects.get(email=otp_instance.email)
                    user.set_password(new_password)
                    user.save()
                    
                    # Mark OTP as used
                    otp_instance.is_used = True
                    otp_instance.save()
                    
                    messages.success(request, 'Password has been reset successfully! Please login with your new password.')
                    return redirect('candidate_login')
                except User.DoesNotExist:
                    messages.error(request, 'User not found.')
                    return redirect('forgot_password')
                    
            except PasswordResetOTP.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please check and try again.')
    else:
        form = PasswordResetConfirmForm()
    
    return render(request, 'candidate/password_reset_confirm.html', {'form': form})

@login_required
def dashboard_view(request):
    profile = CandidateProfile.objects.get(user=request.user)

    # Load persistent AI interview history from DB
    try:
        ai_records = InterviewRecord.objects.filter(candidate=request.user).order_by('-created_at')
    except Exception:
        ai_records = []

    # If resume is parsed and field is available but designation is missing
    if profile.resume and profile.field and not profile.designation:
        return redirect('select_designation')

    return render(request, 'candidate/dashboard.html', {'profile': profile, 'ai_records': ai_records})

@login_required
def upload_resume(request):
    profile = CandidateProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Store current designation before updating
            current_designation = profile.designation
            
            form.save()
            resume_path = profile.resume.path
            data = ResumeParser(resume_path).get_extracted_data()
            profile.parsed_data = data
            skills = [skill.lower() for skill in (data.get('skills') or [])]
            
            # Update field based on skills - more comprehensive detection
            it_skills = ['python', 'java', 'javascript', 'html', 'css', 'sql', 'database', 'api', 'git', 'docker', 'kubernetes', 'aws', 'azure', 'react', 'angular', 'vue', 'node.js', 'php', 'c++', 'c#', '.net', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'tensorflow', 'pytorch', 'machine learning', 'artificial intelligence', 'data science', 'devops', 'cloud computing']
            profile.field = 'IT' if any(skill in skills for skill in it_skills) else 'Non-IT'
            
            # Preserve the designation if it exists and is still valid for the new field
            if current_designation:
                # Check if the designation is still valid for the new field
                it_designations = ['developer', 'engineer', 'programmer', 'analyst', 'architect', 'administrator', 'specialist', 'consultant']
                non_it_designations = ['hr', 'sales', 'marketing', 'manager', 'executive', 'coordinator', 'assistant', 'writer', 'recruiter', 'accountant', 'analyst']
                
                if profile.field == 'IT' and any(tech in current_designation.lower() for tech in it_designations):
                    profile.designation = current_designation
                elif profile.field == 'Non-IT' and any(non_tech in current_designation.lower() for non_tech in non_it_designations):
                    profile.designation = current_designation
                # If designation doesn't match new field, clear it so user can select new one
                else:
                    profile.designation = ''
            else:
                profile.designation = ''
            
            profile.save()
            
            # Show appropriate message
            if profile.designation:
                messages.success(request, 'Resume updated successfully! Your designation has been preserved.')
            else:
                messages.warning(request, 'Resume updated successfully! Please select your designation again as it may not be suitable for the detected field.')
            
            return redirect('candidate_dashboard')
    else:
        form = ResumeUploadForm(instance=profile)
    return render(request, 'candidate/upload_resume.html', {'form': form})

@login_required
def select_designation(request):
    profile = CandidateProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = DesignationForm(field_type=profile.field, data=request.POST)
        if form.is_valid():
            selected_designation = form.cleaned_data['designation']

            profile.designation = selected_designation
            profile.save()

            # Store role and designation in session
            request.session['selected_role'] = profile.field
            request.session['selected_designation'] = selected_designation

            # Clear old questions and answers so new ones will be generated
            request.session.pop('interview_questions', None)
            request.session.pop('interview_answers', None)

            return redirect('candidate_dashboard')
    else:
        form = DesignationForm(field_type=profile.field)

    return render(request, 'candidate/select_designation.html', {
        'form': form,
        'field': profile.field
    })

@login_required
def ai_interview(request):
    profile = CandidateProfile.objects.get(user=request.user)

    # Always clear previous session to start fresh
    request.session.pop('interview_questions', None)
    request.session.pop('interview_answers', None)

    # Generate fresh Gemini-based questions with candidate history
    questions = generate_questions(profile.field, profile.designation, candidate_id=request.user.id)
    request.session['interview_questions'] = questions
    request.session['interview_answers'] = []

    # Redirect to actual Q&A view
    return redirect('interview_question')

@login_required
def interview_question(request):
    questions = request.session.get('interview_questions', [])
    answers = request.session.get('interview_answers', [])
    total_questions = len(questions)
    current_index = len(answers)

    # Interview complete
    if current_index >= total_questions:
        return redirect('interview_complete')

    if request.method == 'POST':
        if 'skip_question' in request.POST:
            answers.append({
                'question': questions[current_index],
                'answer': 'Skipped',
                'mode': 'skipped'
            })
        elif request.POST.get('mode') in ['chat', 'voice']:
            mode = request.POST.get('mode')
            answer = request.POST.get('chat_answer') if mode == 'chat' else request.POST.get('voice_text')
            answers.append({
                'question': questions[current_index],
                'answer': answer,
                'mode': mode
            })

        request.session['interview_answers'] = answers
        return redirect('interview_question')

    return render(request, 'candidate/interview.html', {
        'question': questions[current_index],
        'current_index': current_index,
        'total': total_questions
    })

@login_required
def interview_complete(request):
    answers = request.session.get('interview_answers', [])
    profile = CandidateProfile.objects.get(user=request.user)

    evaluations = []
    total_score = 0
    total_criteria = 0
    all_mistakes = []
    all_improvements = []

    for item in answers:
        if item['answer'] != 'Skipped':
            # Use enhanced evaluation with role and designation context
            result = evaluate_answer(
                item['question'], 
                item['answer'], 
                role=profile.field, 
                designation=profile.designation,
                mode=item['mode']
            )
            if result:
                scores = {k: v for k, v in result.items() if k in ["Relevance and Clarity", "Technical Knowledge", "Communication Skills", "Problem-Solving Approach", "Experience and Examples"]}
                feedback = result.get("Detailed Feedback", "")
                strengths = result.get("Strengths", [])
                improvements = result.get("Areas for Improvement", [])

                avg = sum(scores.values()) / len(scores)
                total_score += avg
                total_criteria += 1

                all_mistakes.extend(strengths)  # Store strengths in all_mistakes for template compatibility
                all_improvements.extend(improvements)

                evaluations.append({
                    'question': item['question'],
                    'answer': item['answer'],
                    'scores': scores,
                    'avg_score': round(avg, 2),
                    'feedback': feedback,
                    'strengths': strengths,
                    'improvements': improvements,
                    'mode': item['mode']
                })
        else:
            evaluations.append({
                'question': item['question'],
                'answer': 'Skipped',
                'scores': {},
                'avg_score': 0,
                'feedback': '',
                'strengths': [],
                'improvements': [],
                'mode': 'skipped'
            })

    interview_record = {
        'date': str(datetime.now().date()),
        'role': profile.field,
        'designation': profile.designation,
        'average': round(total_score / len(answers), 2) if answers else 0,
        'evaluations': evaluations,
        'overall_strengths': all_mistakes,  # Renamed for clarity
        'overall_improvements': all_improvements
    }

    # Persist interview to DB for analytics
    try:
        total_questions = len(answers)
        answered_questions = len([q for q in evaluations if q.get('answer') and q.get('answer') != 'Skipped'])
        skipped_questions = len([q for q in evaluations if q.get('answer') == 'Skipped'])
        InterviewRecord.objects.create(
            candidate=request.user,
            role=profile.field or '',
            designation=profile.designation or '',
            evaluations=evaluations,
            average=interview_record['average'],
            total_questions=total_questions,
            answered_questions=answered_questions,
            skipped_questions=skipped_questions,
        )
    except Exception as e:
        print('Failed to persist interview:', e)

    # Save it in session history (newest first)
    previous = request.session.get('interview_history', [])
    previous.insert(0, interview_record)
    request.session['interview_history'] = previous

    # Clear current session
    request.session.pop('interview_answers', None)

    # Prepare data for template expected fields
    total_questions = len(evaluations)
    answered_questions = len([q for q in evaluations if q.get('answer') and q.get('answer') != 'Skipped'])
    skipped_questions = len([q for q in evaluations if q.get('answer') == 'Skipped'])

    # Map evaluations to a simplified structure for the template (evaluation text + score per question)
    display_evaluations = []
    for ev in evaluations:
        display_evaluations.append({
            'question': ev.get('question', ''),
            'answer': ev.get('answer', ''),
            'mode': ev.get('mode', ''),
            'evaluation': ev.get('feedback', ''),
            'score': ev.get('avg_score', 0),
        })

    return render(request, 'candidate/interview_complete.html', {
        'final_score': round(interview_record['average'] * 20, 2),
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'skipped_questions': skipped_questions,
        'evaluations': display_evaluations,
    })

@login_required
def reset_interview(request):
    request.session.pop('generated_questions', None)
    request.session.pop('interview_answers', None)
    return redirect('ai_interview')

@login_required
def view_ai_evaluation(request, index):
    interview_history = request.session.get('interview_history', [])
    
    if 0 <= index < len(interview_history):
        evaluation = interview_history[index]
        evaluations_list = evaluation.get('evaluations', [])

        return render(request, 'candidate/evaluation_detail.html', {
            'interview': evaluation,
            'final_score': evaluation.get('average', 0) * 20,
            'total_questions': len(evaluations_list),
            'answered_questions': len([q for q in evaluations_list if q.get('answer') and q.get('answer') != 'Skipped']),
            'skipped_questions': len([q for q in evaluations_list if q.get('answer') == 'Skipped']),
            'evaluations': evaluations_list,
            'interview_id': index
        })
    else:
        return redirect('candidate_dashboard')


@login_required
def view_ai_evaluation_db(request, record_id):
    """View a persisted AI interview evaluation stored in DB."""
    try:
        record = InterviewRecord.objects.get(id=record_id, candidate=request.user)
    except InterviewRecord.DoesNotExist:
        return redirect('candidate_dashboard')

    evaluations_list = record.evaluations or []

    return render(request, 'candidate/evaluation_detail.html', {
        'interview': {
            'date': record.created_at.date() if hasattr(record, 'created_at') else None,
            'role': record.role,
            'designation': record.designation,
            'average': record.average,
            'evaluations': evaluations_list,
        },
        'final_score': record.average * 20,
        'total_questions': len(evaluations_list),
        'answered_questions': len([q for q in evaluations_list if q.get('answer') and q.get('answer') != 'Skipped']),
        'skipped_questions': len([q for q in evaluations_list if q.get('answer') == 'Skipped']),
        'evaluations': evaluations_list,
        'interview_id': record.id,
    })

# HR Interview Booking Views
@login_required
def hr_interview_role_selection(request):
    """First step: Select role and designation for HR interview"""
    profile = CandidateProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        # Lock field to resume-detected field if available
        field = profile.field or request.POST.get('field')
        designation = request.POST.get('designation')
        
        if field and designation:
            # Update profile with new field and designation
            profile.field = field
            profile.designation = designation
            profile.save()
            
            # Redirect to HR selection
            return redirect('hr_interview_booking')
        else:
            messages.error(request, 'Please select both field and designation.')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'candidate/hr_interview_role_selection.html', context)

@login_required
def hr_interview_booking(request):
    """Show available HRs for the candidate's designation"""
    profile = CandidateProfile.objects.get(user=request.user)
    
    if not profile.designation:
        messages.error(request, 'Please select your designation first.')
        return redirect('hr_interview_role_selection')
    
    # Fetch active HRs and filter in Python to avoid JSON contains lookup unsupported on SQLite
    designation_normalized = (profile.designation or '').strip().lower()
    active_hrs = HR.objects.filter(is_active=True)
    available_hrs = []
    for hr in active_hrs:
        try:
            handled = hr.designations_handled or []
            # Normalize to lowercase strings
            handled_norm = [str(x).strip().lower() for x in handled]
            if designation_normalized in handled_norm:
                available_hrs.append(hr)
        except Exception:
            # If malformed data, skip this HR
            continue
    
    context = {
        'profile': profile,
        'available_hrs': available_hrs,
    }
    
    return render(request, 'candidate/hr_interview_booking.html', context)

@login_required
def hr_time_slots(request, hr_id):
    """Show available time slots for a specific HR"""
    try:
        hr = HR.objects.get(id=hr_id, is_active=True)
        profile = CandidateProfile.objects.get(user=request.user)
        
        # Get available time slots for this HR
        available_slots = HRTimeSlot.objects.filter(
            hr=hr,
            is_available=True,
            date__gte=datetime.now().date()
        ).order_by('date', 'start_time')
        
        # Exclude past slots for today
        from datetime import datetime as _dt
        now = _dt.now()
        filtered_slots = []
        for s in available_slots:
            slot_dt = _dt.combine(s.date, s.start_time)
            if slot_dt > now:
                filtered_slots.append(s)
        
        context = {
            'hr': hr,
            'profile': profile,
            'available_slots': filtered_slots,
            'today': now.date(),
        }
        
        return render(request, 'candidate/hr_time_slots.html', context)
        
    except HR.DoesNotExist:
        messages.error(request, 'HR not found.')
        return redirect('hr_interview_booking')

@login_required
def book_hr_interview(request, hr_id, slot_id):
    """Book an HR interview slot"""
    try:
        hr = HR.objects.get(id=hr_id, is_active=True)
        time_slot = HRTimeSlot.objects.get(id=slot_id, hr=hr, is_available=True)
        profile = CandidateProfile.objects.get(user=request.user)
        
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

@login_required
def hr_booking_confirmation(request, booking_id):
    """Show booking confirmation with meeting details"""
    try:
        booking = HRInterviewBooking.objects.get(id=booking_id, candidate=request.user)
        
        context = {
            'booking': booking,
        }
        
        return render(request, 'candidate/hr_booking_confirmation.html', context)
        
    except HRInterviewBooking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('candidate_dashboard')

@login_required
def hr_interview_history(request):
    """Show candidate's HR interview history with real-time status tracking"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    now = timezone.now()
    current_time = now.time()
    current_date = now.date()
    
    all_bookings = HRInterviewBooking.objects.filter(candidate=request.user).order_by('-created_at')
    
    upcoming_bookings = []
    missed_bookings = []
    completed_bookings = []
    
    for booking in all_bookings:
        if booking.status == 'completed':
            completed_bookings.append(booking)
        elif booking.status == 'scheduled':
            interview_start = datetime.combine(booking.time_slot.date, booking.time_slot.start_time)
            interview_end = datetime.combine(booking.time_slot.date, booking.time_slot.end_time)
            if interview_start.date() < current_date:
                booking.status = 'no_show'
                booking.save()
                missed_bookings.append(booking)
                continue
            if interview_start.date() == current_date:
                # Past end -> if >10 minutes after end, mark as no_show
                minutes_after_end = (datetime.combine(current_date, current_time) - interview_end).total_seconds() / 60
                if minutes_after_end > 10:
                    booking.status = 'no_show'
                    booking.save()
                    missed_bookings.append(booking)
                elif minutes_after_end >= -40:  # from 30 min slot start until 10 min after end
                    upcoming_bookings.append(booking)
                else:
                    # Not yet started today
                    upcoming_bookings.append(booking)
            else:
                # Future date
                upcoming_bookings.append(booking)
        elif booking.status in ['no_show', 'cancelled']:
            # Combine cancelled and no_show as "missed" interviews
            missed_bookings.append(booking)
    
    # Sort each section by nearest date/time first (ascending order)
    upcoming_bookings.sort(key=lambda x: (x.time_slot.date, x.time_slot.start_time))
    completed_bookings.sort(key=lambda x: (x.time_slot.date, x.time_slot.start_time), reverse=True)  # Most recent first
    missed_bookings.sort(key=lambda x: (x.time_slot.date, x.time_slot.start_time), reverse=True)  # Most recent first
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'missed_bookings': missed_bookings,
        'completed_bookings': completed_bookings,
        'current_time': current_time,
        'current_date': current_date,
    }
    
    return render(request, 'candidate/hr_interview_history.html', context)

@login_required
def upcoming_hr_interviews(request):
    """Show only upcoming HR interviews with join buttons"""
    from datetime import datetime, timedelta
    
    # Use naive local time consistently (to match stored slot times)
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    
    all_bookings = HRInterviewBooking.objects.filter(candidate=request.user).order_by('-created_at')
    
    upcoming_bookings = []
    
    for booking in all_bookings:
        if booking.status == 'scheduled':
            interview_start = datetime.combine(booking.time_slot.date, booking.time_slot.start_time)
            interview_end = datetime.combine(booking.time_slot.date, booking.time_slot.end_time)
            if interview_start.date() < current_date:
                booking.status = 'no_show'
                booking.save()
                continue
            if interview_start.date() == current_date:
                # Past end -> if >10 minutes after end, mark as no_show
                minutes_after_end = (datetime.combine(current_date, current_time) - interview_end).total_seconds() / 60
                if minutes_after_end > 10:
                    booking.status = 'no_show'
                    booking.save()
                elif minutes_after_end >= -40:  # from 30 min slot start until 10 min after end
                    upcoming_bookings.append(booking)
                else:
                    upcoming_bookings.append(booking)
            else:
                upcoming_bookings.append(booking)
    
    # Sort by nearest date/time first (ascending order)
    upcoming_bookings.sort(key=lambda x: (x.time_slot.date, x.time_slot.start_time))
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'current_time': current_time,
        'current_date': current_date,
    }
    
    return render(request, 'candidate/upcoming_hr_interviews.html', context)

@login_required
def view_hr_feedback(request, booking_id):
    """Candidate can view HR feedback for their interview"""
    try:
        booking = HRInterviewBooking.objects.get(id=booking_id, candidate=request.user)
        
        try:
            feedback = HRInterviewFeedback.objects.get(booking=booking)
        except HRInterviewFeedback.DoesNotExist:
            messages.info(request, 'No feedback available yet for this interview.')
            return redirect('hr_interview_history')
        
        # Get replies
        replies = feedback.replies.all()
        
        context = {
            'booking': booking,
            'feedback': feedback,
            'replies': replies,
        }
        
        return render(request, 'candidate/view_hr_feedback.html', context)
        
    except HRInterviewBooking.DoesNotExist:
        messages.error(request, 'Interview not found.')
        return redirect('hr_interview_history')

@login_required
def reply_to_feedback(request, feedback_id):
    """Candidate can reply to HR feedback"""
    try:
        feedback = HRInterviewFeedback.objects.get(id=feedback_id, candidate=request.user)
        
        if request.method == 'POST':
            reply_text = request.POST.get('reply_text', '').strip()
            
            if reply_text:
                CandidateFeedbackReply.objects.create(
                    feedback=feedback,
                    candidate=request.user,
                    reply_text=reply_text
                )
                messages.success(request, 'Your reply has been submitted successfully!')
                return redirect('view_hr_feedback', booking_id=feedback.booking.id)
            else:
                messages.error(request, 'Please enter a reply.')
        
        context = {
            'feedback': feedback,
        }
        
        return render(request, 'candidate/reply_to_feedback.html', context)
        
    except HRInterviewFeedback.DoesNotExist:
        messages.error(request, 'Feedback not found.')
        return redirect('hr_interview_history')

def track_candidate_attendance(request, booking_id):
    """API endpoint to track candidate meeting attendance"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        booking = HRInterviewBooking.objects.get(
            id=booking_id,
            candidate=request.user
        )

        action = request.POST.get('action')

        if action == 'candidate_joined':
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


def test_email(request):
    success = send_brevo_email(
        "karthikpoojary0704@gmail.com",
        "Brevo API Working",
        "<h2>Brevo Email API is Working Successfully 🎉</h2>",
    )

    if success:
        return HttpResponse("Email sent using Brevo API")
    else:
        return HttpResponse("Email failed")