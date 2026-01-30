from django.db import models
from django.contrib.auth.models import User
import hashlib
import random
import string
from datetime import datetime, timedelta
import uuid

class HR(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    FIELD_CHOICES = [
        ('IT', 'IT'),
        ('Non-IT', 'Non-IT'),
    ]
    
    # Basic Personal Details
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    
    # Professional Details
    field_of_expertise = models.CharField(max_length=10, choices=FIELD_CHOICES)
    designations_handled = models.JSONField(default=list)  # Store as list of designations
    years_of_experience = models.IntegerField()
    specialization_skills = models.TextField(blank=True, null=True)
    
    # Login Credentials
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)  # Hashed password
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def generate_password(self):
        """Generate a 6-character password with one capital letter and one special character"""
        # Generate 4 random lowercase letters
        letters = ''.join(random.choices(string.ascii_lowercase, k=4))
        # Add one capital letter
        capital = random.choice(string.ascii_uppercase)
        # Add one special character
        special = random.choice('!@#$%^&*')
        # Combine and shuffle
        password = letters + capital + special
        password_list = list(password)
        random.shuffle(password_list)
        return ''.join(password_list)
    
    def set_password(self, password=None):
        """Set password - generate if not provided"""
        if password is None:
            password = self.generate_password()
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.password = hashed_password
        return password  # Return plain password for email
    
    def check_password(self, password):
        """Check if provided password matches"""
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return self.password == hashed_password
    
    class Meta:
        verbose_name = "HR"
        verbose_name_plural = "HRs"

class HRTimeSlot(models.Model):
    """HR available time slots for interviews"""
    hr = models.ForeignKey(HR, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()  # 9:00 AM to 5:00 PM
    end_time = models.TimeField()    # 30 minutes later
    is_available = models.BooleanField(default=True)
    is_managed = models.BooleanField(default=False)  # HR can manage this slot
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['hr', 'date', 'start_time']
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.hr.full_name} - {self.date} {self.start_time}"
    
    @property
    def time_display(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"
    
    @property
    def safe_end_time(self):
        """Return a corrected end time if saved end_time is not after start_time."""
        from datetime import datetime, timedelta
        try:
            if self.end_time <= self.start_time:
                start_dt = datetime.combine(self.date, self.start_time)
                corrected = (start_dt + timedelta(minutes=30)).time()
                return corrected
            return self.end_time
        except Exception:
            # Fallback to 30 minutes after start on any error
            start_dt = datetime.combine(self.date, self.start_time)
            return (start_dt + timedelta(minutes=30)).time()
    
    @property
    def safe_time_display(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.safe_end_time.strftime('%I:%M %p')}"
    
    @property
    def is_booked(self):
        return hasattr(self, 'interview_booking')

class HRInterviewBooking(models.Model):
    """HR interview bookings by candidates"""
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hr_bookings')
    hr = models.ForeignKey(HR, on_delete=models.CASCADE, related_name='interview_bookings')
    time_slot = models.OneToOneField(HRTimeSlot, on_delete=models.CASCADE, related_name='interview_booking')
    designation = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], default='scheduled')
    
    # Jitsi Meet Integration
    meeting_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    meeting_url = models.URLField(blank=True, null=True)
    meeting_password = models.CharField(max_length=50, blank=True, null=True)
    
    # Interview Attendance Tracking (will be added via migration)
    hr_joined_at = models.DateTimeField(blank=True, null=True, help_text="When HR joined the meeting")
    candidate_joined_at = models.DateTimeField(blank=True, null=True, help_text="When candidate joined the meeting")
    hr_left_at = models.DateTimeField(blank=True, null=True, help_text="When HR left the meeting")
    candidate_left_at = models.DateTimeField(blank=True, null=True, help_text="When candidate left the meeting")
    actual_duration_minutes = models.IntegerField(default=0, help_text="Actual interview duration in minutes")
    both_attended = models.BooleanField(default=False, help_text="Whether both HR and candidate attended")
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.candidate.email} - {self.hr.full_name} - {self.time_slot.date}"
    
    def save(self, *args, **kwargs):
        # Generate meeting ID and URL if not exists
        if not self.meeting_id:
            self.meeting_id = f"interview-{uuid.uuid4().hex[:8]}"
            # Add config parameters to allow joining without waiting for moderator
            self.meeting_url = f"https://meet.jit.si/{self.meeting_id}#config.requireDisplayName=false&config.disableDeepLinking=true&config.prejoinPageEnabled=false"
            self.meeting_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # When booking is created, mark time slot as unavailable
        if not self.pk:  # New booking
            self.time_slot.is_available = False
            self.time_slot.is_managed = False  # HR can no longer manage this slot
            self.time_slot.save()
        super().save(*args, **kwargs)
    
    @property
    def is_meeting_ready(self):
        """Allow joining within 10 minutes after the start time."""
        if not self.time_slot:
            return False
        
        from datetime import datetime
        now = datetime.now()
        meeting_datetime = datetime.combine(self.time_slot.date, self.time_slot.start_time)
        minutes_after_start = (now - meeting_datetime).total_seconds() / 60
        return 0 <= minutes_after_start <= 10
    
    def mark_hr_joined(self):
        """Mark when HR joins the meeting"""
        from django.utils import timezone
        if not self.hr_joined_at:
            self.hr_joined_at = timezone.now()
            self.save()
    
    def mark_candidate_joined(self):
        """Mark when candidate joins the meeting"""
        from django.utils import timezone
        if not self.candidate_joined_at:
            self.candidate_joined_at = timezone.now()
            self.check_and_complete_interview()
            self.save()
    
    def mark_hr_left(self):
        """Mark when HR leaves the meeting"""
        from django.utils import timezone
        if not self.hr_left_at:
            self.hr_left_at = timezone.now()
            self.calculate_duration()
            self.save()
    
    def mark_candidate_left(self):
        """Mark when candidate leaves the meeting"""
        from django.utils import timezone
        if not self.candidate_left_at:
            self.candidate_left_at = timezone.now()
            self.calculate_duration()
            self.save()
    
    def check_and_complete_interview(self):
        """Check if both joined and auto-complete if duration is sufficient"""
        if self.hr_joined_at and self.candidate_joined_at:
            # Both joined - check if we should auto-complete
            from django.utils import timezone
            now = timezone.now()
            
            # Calculate duration since both joined
            start_time = max(self.hr_joined_at, self.candidate_joined_at)
            duration = (now - start_time).total_seconds() / 60
            
            # Auto-complete if both attended for 5+ minutes
            if duration >= 5 and self.status == 'scheduled':
                self.status = 'completed'
                self.both_attended = True
                self.actual_duration_minutes = int(duration)
    
    def calculate_duration(self):
        """Calculate actual interview duration"""
        if self.hr_joined_at and self.candidate_joined_at:
            # Both joined - calculate overlap duration
            start_time = max(self.hr_joined_at, self.candidate_joined_at)
            end_time = None
            
            if self.hr_left_at and self.candidate_left_at:
                end_time = min(self.hr_left_at, self.candidate_left_at)
            elif self.hr_left_at:
                end_time = self.hr_left_at
            elif self.candidate_left_at:
                end_time = self.candidate_left_at
            
            if end_time:
                duration = (end_time - start_time).total_seconds() / 60
                self.actual_duration_minutes = max(0, int(duration))
                
                # Mark as both attended if duration >= 5 minutes
                if self.actual_duration_minutes >= 5:
                    self.both_attended = True
                    if self.status == 'scheduled':
                        self.status = 'completed'
    
    @property
    def is_eligible_for_feedback(self):
        """Check if interview is eligible for feedback"""
        return self.status == 'completed' and self.both_attended and self.actual_duration_minutes >= 5
    
    @property
    def attendance_summary(self):
        """Get attendance summary"""
        if not self.hr_joined_at and not self.candidate_joined_at:
            return "No attendance recorded"
        elif self.hr_joined_at and not self.candidate_joined_at:
            return "Only HR attended"
        elif not self.hr_joined_at and self.candidate_joined_at:
            return "Only candidate attended"
        elif self.both_attended:
            return f"Both attended ({self.actual_duration_minutes} minutes)"
        else:
            return "Both joined but insufficient duration"

class HRInterviewFeedback(models.Model):
    """HR feedback for completed interviews"""
    booking = models.OneToOneField(HRInterviewBooking, on_delete=models.CASCADE, related_name='feedback')
    hr = models.ForeignKey(HR, on_delete=models.CASCADE, related_name='given_feedbacks')
    candidate = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='received_feedbacks')
    
    # Evaluation Criteria (1-5 scale)
    relevance_clarity = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="How well the candidate addressed questions and communicated ideas")
    technical_knowledge = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Demonstration of role-specific technical skills and knowledge")
    communication_skills = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Ability to articulate thoughts clearly and professionally")
    problem_solving = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Logical thinking and systematic approach to problems")
    experience_examples = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Use of relevant examples and practical experience")
    
    # Overall Assessment
    overall_score = models.FloatField(help_text="Average of all criteria scores")
    
    # Detailed Feedback
    strengths = models.JSONField(default=list, help_text="List of candidate strengths")
    areas_for_improvement = models.JSONField(default=list, help_text="List of areas for improvement")
    detailed_feedback = models.TextField(help_text="Comprehensive feedback explaining the evaluation")
    recommendation = models.TextField(help_text="Brief recommendation for this candidate")
    
    # Additional HR Notes
    additional_notes = models.TextField(blank=True, null=True, help_text="Additional HR notes or observations")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback for {self.candidate.email} by {self.hr.full_name}"
    
    def save(self, *args, **kwargs):
        # Calculate overall score
        scores = [
            self.relevance_clarity,
            self.technical_knowledge,
            self.communication_skills,
            self.problem_solving,
            self.experience_examples
        ]
        self.overall_score = sum(scores) / len(scores)
        super().save(*args, **kwargs)

class CandidateFeedbackReply(models.Model):
    """Candidate's reply to HR feedback"""
    feedback = models.ForeignKey(HRInterviewFeedback, on_delete=models.CASCADE, related_name='replies')
    candidate = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='feedback_replies')
    
    reply_text = models.TextField(help_text="Candidate's reply to the feedback")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reply from {self.candidate.email} to feedback {self.feedback.id}"
