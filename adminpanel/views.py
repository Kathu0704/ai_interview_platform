# adminpanel/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Admin
from .forms import HRRegistrationForm, HREditForm
from hr.models import HR
from candidate.models import CandidateProfile, InterviewRecord
import hashlib

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Hash the password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            admin = Admin.objects.get(email=email, password=hashed_password, is_active=True)
            # Store admin info in session
            request.session['admin_id'] = admin.id
            request.session['admin_email'] = admin.email
            request.session['admin_name'] = admin.name
            return redirect('admin_dashboard')
        except Admin.DoesNotExist:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'adminpanel/login.html')


def dashboard_view(request):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    admin_name = request.session.get('admin_name', 'Admin')

    # Aggregate basic stats (extend later if interview tracking is persisted)
    total_candidates = CandidateProfile.objects.count()
    total_hrs = HR.objects.count()
    ai_interviews_conducted = InterviewRecord.objects.count()
    hr_interviews_conducted = 0  # Placeholder

    # Recent activity samples
    recent_candidates = CandidateProfile.objects.select_related('user').order_by('-id')[:5]
    recent_hrs = HR.objects.order_by('-created_at')[:5]

    context = {
        'admin_name': admin_name,
        'total_candidates': total_candidates,
        'total_hrs': total_hrs,
        'ai_interviews_conducted': ai_interviews_conducted,
        'hr_interviews_conducted': hr_interviews_conducted,
        'recent_candidates': recent_candidates,
        'recent_hrs': recent_hrs,
    }
    return render(request, 'adminpanel/dashboard.html', context)

def logout_view(request):
    # Clear session
    request.session.flush()
    return redirect('admin_login')

def hr_registration_view(request):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')
    
    if request.method == 'POST':
        form = HRRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create HR with email as username
                hr = form.save(commit=False)
                hr.username = form.cleaned_data['email']

                # Set provided password (hashed in model method)
                provided_password = form.cleaned_data['password']
                hr.set_password(provided_password)

                # Save the HR object
                hr.save()

                messages.success(request, f"HR '{hr.full_name}' registered successfully.")
                return redirect('manage_hr')

            except Exception as e:
                messages.error(request, f'Error registering HR: {str(e)}')
    else:
        form = HRRegistrationForm()
    
    context = {
        'form': form,
        'admin_name': request.session.get('admin_name', 'Admin')
    }
    return render(request, 'adminpanel/hr_registration.html', context)


def manage_hr_view(request):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    hrs = HR.objects.order_by('-created_at')
    return render(request, 'adminpanel/manage_hr.html', {
        'hrs': hrs,
        'admin_name': request.session.get('admin_name', 'Admin'),
    })


def toggle_hr_active_view(request, hr_id):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    try:
        hr = HR.objects.get(id=hr_id)
        hr.is_active = not hr.is_active
        hr.save()
        state = 'activated' if hr.is_active else 'deactivated'
        messages.success(request, f"HR '{hr.full_name}' has been {state}.")
    except HR.DoesNotExist:
        messages.error(request, 'HR not found.')
    return redirect('manage_hr')


def edit_hr_view(request, hr_id):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    try:
        hr = HR.objects.get(id=hr_id)
    except HR.DoesNotExist:
        messages.error(request, 'HR not found.')
        return redirect('manage_hr')

    if request.method == 'POST':
        form = HREditForm(request.POST, instance=hr)
        if form.is_valid():
            form.save()
            messages.success(request, 'HR details updated successfully.')
            return redirect('manage_hr')
    else:
        form = HREditForm(instance=hr)

    return render(request, 'adminpanel/edit_hr.html', {
        'form': form,
        'hr': hr,
        'admin_name': request.session.get('admin_name', 'Admin'),
    })


def manage_candidates_view(request):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    candidates = CandidateProfile.objects.select_related('user').order_by('-user__date_joined')
    return render(request, 'adminpanel/manage_candidates.html', {
        'candidates': candidates,
        'admin_name': request.session.get('admin_name', 'Admin'),
    })


def analytics_view(request):
    # Require admin session
    if 'admin_id' not in request.session:
        return redirect('admin_login')

    total_interviews = InterviewRecord.objects.count()
    avg_score = 0
    top_designations = []
    if total_interviews:
        from django.db.models import Avg, Count
        avg_score = InterviewRecord.objects.aggregate(avg=Avg('average'))['avg'] or 0
        top_designations = (
            InterviewRecord.objects.values('designation')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )

    recent = InterviewRecord.objects.select_related('candidate').order_by('-created_at')[:10]

    return render(request, 'adminpanel/analytics.html', {
        'admin_name': request.session.get('admin_name', 'Admin'),
        'total_interviews': total_interviews,
        'avg_score': round(avg_score, 2) if avg_score else 0,
        'top_designations': top_designations,
        'recent': recent,
    })
