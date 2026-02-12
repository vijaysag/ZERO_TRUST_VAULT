from django.urls import path
from data_management import views

app_name = 'data_management'

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('upload/', views.upload_data, name='upload_data'),
    path('view/', views.view_data, name='view_data'),
    path('modify/<str:data_id>/', views.modify_data, name='modify_data'),
    path('delete/<str:data_id>/', views.delete_data, name='delete_data'),
    path('requests/', views.view_requests, name='view_requests'),
    path('requests/<int:request_id>/process/', views.process_request, name='process_request'),
]
