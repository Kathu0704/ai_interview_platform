from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='admin_login'),
    path('register/', views.admin_register_view, name='admin_register'),
    path('dashboard/', views.dashboard_view, name='admin_dashboard'),
    path('logout/', views.logout_view, name='admin_logout'),
    path('hr-registration/', views.hr_registration_view, name='hr_registration'),
    path('manage-hr/', views.manage_hr_view, name='manage_hr'),
    path('edit-hr/<int:hr_id>/', views.edit_hr_view, name='edit_hr'),
    path('toggle-hr/<int:hr_id>/', views.toggle_hr_active_view, name='toggle_hr_active'),
    path('candidates/', views.manage_candidates_view, name='manage_candidates'),
    path('analytics/', views.analytics_view, name='admin_analytics'),
]
