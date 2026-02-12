from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('', core_views.login_view, name='home'),
    path('register/', core_views.register_view, name='register'),
    path('login/', core_views.login_view, name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    path('mfa/setup/', core_views.mfa_setup, name='mfa_setup'),
    path('mfa/verify/', core_views.mfa_verify, name='mfa_verify'),
    path('profile/', core_views.profile_view, name='profile'),
    path('profile/toggle-2fa/', core_views.toggle_2fa, name='toggle_2fa'),
    path('profile/register-blockchain/', core_views.register_blockchain, name='register_blockchain'),
    
    # API endpoints
    path('api/resend-otp/', core_views.resend_otp_api, name='resend_otp_api'),
    
    # Admin routes
    path('admin-dashboard/', include('data_management.urls')),
    
    # User routes
    path('dashboard/', include('access_control.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
