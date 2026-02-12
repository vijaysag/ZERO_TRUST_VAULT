from django.urls import path
from access_control import views

app_name = 'access_control'

urlpatterns = [
    path('', views.user_dashboard, name='user_dashboard'),
    path('browse/', views.browse_data, name='browse_data'),
    path('request/<str:data_id>/', views.request_data_access, name='request_data_access'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('view/<int:request_id>/', views.view_data_with_otp, name='view_data_with_otp'),
    path('download/<int:request_id>/', views.download_data, name='download_data'),
    path('api/resend-data-otp/', views.resend_data_access_otp, name='resend_data_access_otp'),
]
