from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='candidate_register'),
    path('login/', views.login_view, name='candidate_login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='candidate_dashboard'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('select-designation/', views.select_designation, name='select_designation'),
    path('ai-interview/', views.ai_interview, name='ai_interview'),
    path('interview-question/', views.interview_question, name='interview_question'),
    path('interview-complete/', views.interview_complete, name='interview_complete'),
    path('reset-interview/', views.reset_interview, name='reset_interview'),
    path('view-evaluation/<int:index>/', views.view_ai_evaluation, name='view_ai_evaluation'),
    path('view-evaluation-db/<int:record_id>/', views.view_ai_evaluation_db, name='view_ai_evaluation_db'),
    path('email-confirmation/', views.email_confirmation_view, name='email_confirmation'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('password-reset-confirm/', views.password_reset_confirm_view, name='password_reset_confirm'),
    
    # HR Interview Booking URLs
    path('hr-interview-role-selection/', views.hr_interview_role_selection, name='hr_interview_role_selection'),
    path('hr-interview-booking/', views.hr_interview_booking, name='hr_interview_booking'),
    path('hr-time-slots/<int:hr_id>/', views.hr_time_slots, name='hr_time_slots'),
    path('book-hr-interview/<int:hr_id>/<int:slot_id>/', views.book_hr_interview, name='book_hr_interview'),
    path('hr-booking-confirmation/<int:booking_id>/', views.hr_booking_confirmation, name='hr_booking_confirmation'),
    path('hr-interview-history/', views.hr_interview_history, name='hr_interview_history'),
    path('upcoming-hr-interviews/', views.upcoming_hr_interviews, name='upcoming_hr_interviews'),
    path('view-hr-feedback/<int:booking_id>/', views.view_hr_feedback, name='view_hr_feedback'),
    path('reply-to-feedback/<int:feedback_id>/', views.reply_to_feedback, name='reply_to_feedback'),
    path('track-candidate-attendance/<int:booking_id>/', views.track_candidate_attendance, name='track_candidate_attendance'),
]
