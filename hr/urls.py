from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='hr_login'),
    path('forgot-password/', views.forgot_password_view, name='hr_forgot_password'),
    path('reset-password/', views.reset_password_view, name='hr_reset_password'),
    path('dashboard/', views.dashboard_view, name='hr_dashboard'),
    path('manage-time-slots/', views.manage_time_slots_view, name='hr_manage_time_slots'),
    path('manage-interviews/', views.manage_interviews_view, name='hr_manage_interviews'),
    path('join-interview/<int:booking_id>/', views.join_interview_view, name='hr_join_interview'),
    path('complete-interview/<int:booking_id>/', views.complete_interview_view, name='hr_complete_interview'),
    path('track-attendance/<int:booking_id>/', views.track_attendance_view, name='hr_track_attendance'),
    path('booked-time-slots/', views.booked_time_slots_view, name='hr_booked_time_slots'),
    path('interviews/conducted/', views.interviews_conducted_list_view, name='hr_interviews_conducted'),
    path('interviews/today/', views.todays_interviews_list_view, name='hr_interviews_today'),
    path('interviews/upcoming/', views.upcoming_interviews_list_view, name='hr_interviews_upcoming'),
    path('candidates/', views.view_candidates_view, name='hr_view_candidates'),
    path('analytics/', views.analytics_view, name='hr_analytics'),
    path('give-feedback/<int:booking_id>/', views.give_feedback_view, name='hr_give_feedback'),
    path('view-feedback/<int:booking_id>/', views.view_feedback_view, name='hr_view_feedback'),
    path('logout/', views.logout_view, name='hr_logout'),
]