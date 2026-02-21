from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
import string
from ai_interview_platform.supabase_storage import SupabaseStorage


class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Store resumes as Cloudinary “raw” files so PDFs are accessible via URL
    resume = models.FileField(
        storage=SupabaseStorage(),
        upload_to='resumes/',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)  # Full Name
    dob = models.DateField(null=True, blank=True)
    field = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username

class EmailConfirmationOTP(models.Model):
    """OTP for email confirmation during registration"""
    email = models.EmailField()
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.email} - {self.otp}"
    
    def is_expired(self):
        """Check if OTP has expired (10 minutes)"""
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry_time
    
    def generate_otp(self):
        """Generate a new 4-digit OTP"""
        self.otp = ''.join(random.choices(string.digits, k=4))
        self.save()
        return self.otp
    
    @classmethod
    def create_otp(cls, email):
        """Create or update OTP for an email"""
        # Delete any existing unused OTPs for this email
        cls.objects.filter(email=email, is_used=False).delete()
        
        # Create new OTP
        otp_instance = cls.objects.create(email=email)
        otp_instance.generate_otp()
        return otp_instance

class PasswordResetOTP(models.Model):
    """OTP for password reset"""
    email = models.EmailField()
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.email} - {self.otp}"
    
    def is_expired(self):
        """Check if OTP has expired (10 minutes)"""
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry_time
    
    def generate_otp(self):
        """Generate a new 4-digit OTP"""
        self.otp = ''.join(random.choices(string.digits, k=4))
        self.save()
        return self.otp
    
    @classmethod
    def create_otp(cls, email):
        """Create or update OTP for an email"""
        # Delete any existing unused OTPs for this email
        cls.objects.filter(email=email, is_used=False).delete()
        
        # Create new OTP
        otp_instance = cls.objects.create(email=email)
        otp_instance.generate_otp()
        return otp_instance
    
class InterviewRecord(models.Model):
    """Persistent record of an AI interview for analytics and history."""
    candidate = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    evaluations = models.JSONField(default=list)
    average = models.FloatField(default=0)
    total_questions = models.IntegerField(default=0)
    answered_questions = models.IntegerField(default=0)
    skipped_questions = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Interview {self.id} - {self.candidate.email} - {self.designation}"
    
   