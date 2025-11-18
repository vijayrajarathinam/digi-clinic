from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name= 'logout'),

    # token management
    path('token/refresh/', TokenRefreshView.as_view(), name= 'token_refresh'),
    path('token/refresh/custom/', views.token_refresh_custom, name='token_refresh_custom'),
    path('token/validate/', views.validate_token, name= 'token_validate'),
    
    # user profile
    path('profile/', views.user_profile, name='user_profile'),
    path('verify-email/', views.verify_email, name='user_verify_email'),
    path('resend-verification/', views.resend_verification_email, name='user_resend_verification'),
    path('send-verification/', views.send_verification_email_authenticated, name='user_send_verification')

] # fmt: skip
