from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from data_management.models import DataFile, DataModificationLog
from access_control.models import AccessRequest, DataAccessLog
from blockchain.services import blockchain_service
from core.services import OTPService
import os


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.is_admin()


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard view"""
    # Get statistics
    total_files = DataFile.objects.filter(status='active').count()
    total_users = User.objects.filter(role='user').count()
    pending_requests = AccessRequest.objects.filter(status='pending').count()
    total_requests = AccessRequest.objects.count()
    
    # Recent requests
    recent_requests = AccessRequest.objects.select_related(
        'user', 'data_file'
    ).order_by('-requested_at')[:10]
    
    # Recent uploads
    recent_uploads = DataFile.objects.filter(
        status='active'
    ).order_by('-uploaded_at')[:5]
    
    context = {
        'total_files': total_files,
        'total_users': total_users,
        'pending_requests': pending_requests,
        'total_requests': total_requests,
        'recent_requests': recent_requests,
        'recent_uploads': recent_uploads,
    }
    
    return render(request, 'data_management/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def upload_data(request):
    """Upload data file view"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            file = request.FILES.get('file')
            
            if not title or not file:
                messages.error(request, 'Title and file are required')
                return render(request, 'data_management/upload_data.html')
            
            # Validate file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                messages.error(request, f'File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB')
                return render(request, 'data_management/upload_data.html')
            
            # Validate file type
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in settings.ALLOWED_FILE_TYPES:
                messages.error(request, f'File type .{file_ext} is not allowed')
                return render(request, 'data_management/upload_data.html')
            
            # Create data file
            data_file = DataFile.objects.create(
                title=title,
                description=description,
                file=file,
                file_type=file_ext,
                file_size=file.size,
                uploaded_by=request.user,
                status='active'
            )
            
            # Record on blockchain
            if blockchain_service.contract:
                result = blockchain_service.record_data_upload(
                    data_file.data_id,
                    data_file.title,
                    request.user.wallet_address or request.user.username,
                    ''  # IPFS hash placeholder
                )
                
                if result:
                    data_file.blockchain_tx_hash = result['tx_hash']
                    data_file.save()
            
            # Log modification
            DataModificationLog.objects.create(
                data_file=data_file,
                action='upload',
                performed_by=request.user,
                details=f'Uploaded file: {file.name}',
                blockchain_tx_hash=data_file.blockchain_tx_hash
            )
            
            messages.success(request, f'File "{title}" uploaded successfully!')
            return redirect('data_management:view_data')
            
        except Exception as e:
            messages.error(request, f'Upload failed: {str(e)}')
            return render(request, 'data_management/upload_data.html')
    
    return render(request, 'data_management/upload_data.html')


@login_required
@user_passes_test(is_admin)
def view_data(request):
    """View all data files"""
    files = DataFile.objects.filter(status='active').order_by('-uploaded_at')
    
    return render(request, 'data_management/view_data.html', {
        'files': files
    })


@login_required
@user_passes_test(is_admin)
def modify_data(request, data_id):
    """Modify data file"""
    data_file = get_object_or_404(DataFile, data_id=data_id, status='active')
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            
            if not title:
                messages.error(request, 'Title is required')
                return render(request, 'data_management/modify_data.html', {'data_file': data_file})
            
            old_title = data_file.title
            data_file.title = title
            data_file.description = description
            data_file.save()
            
            # Log modification
            DataModificationLog.objects.create(
                data_file=data_file,
                action='modify',
                performed_by=request.user,
                details=f'Changed title from "{old_title}" to "{title}"'
            )
            
            messages.success(request, 'Data file updated successfully!')
            return redirect('data_management:view_data')
            
        except Exception as e:
            messages.error(request, f'Update failed: {str(e)}')
    
    return render(request, 'data_management/modify_data.html', {'data_file': data_file})


@login_required
@user_passes_test(is_admin)
def delete_data(request, data_id):
    """Delete (soft delete) data file"""
    data_file = get_object_or_404(DataFile, data_id=data_id, status='active')
    
    if request.method == 'POST':
        data_file.status = 'deleted'
        data_file.save()
        
        # Log modification
        DataModificationLog.objects.create(
            data_file=data_file,
            action='delete',
            performed_by=request.user,
            details=f'Deleted file: {data_file.title}'
        )
        
        messages.success(request, 'Data file deleted successfully!')
        return redirect('data_management:view_data')
    
    return render(request, 'data_management/delete_data.html', {'data_file': data_file})


@login_required
@user_passes_test(is_admin)
def view_requests(request):
    """View all access requests"""
    status_filter = request.GET.get('status', 'all')
    
    requests_query = AccessRequest.objects.select_related('user', 'data_file')
    
    if status_filter != 'all':
        requests_query = requests_query.filter(status=status_filter)
    
    requests_list = requests_query.order_by('-requested_at')
    
    return render(request, 'data_management/view_requests.html', {
        'requests': requests_list,
        'status_filter': status_filter
    })


@login_required
@user_passes_test(is_admin)
def process_request(request, request_id):
    """Process (approve/reject) access request"""
    access_request = get_object_or_404(AccessRequest, request_id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            access_request.approve(request.user, admin_notes)
            
            # Record on blockchain
            if blockchain_service.contract:
                result = blockchain_service.process_access_request(
                    access_request.request_id,
                    True
                )
                if result:
                    access_request.blockchain_approval_tx = result['tx_hash']
                    access_request.save()
            
            # Send OTP to user
            OTPService.generate_otp(access_request.user, purpose='data_access')
            access_request.access_otp_sent = True
            access_request.save()
            
            messages.success(request, f'Request approved! OTP sent to {access_request.user.username}')
        
        elif action == 'reject':
            access_request.reject(request.user, admin_notes)
            
            # Record on blockchain
            if blockchain_service.contract:
                result = blockchain_service.process_access_request(
                    access_request.request_id,
                    False
                )
                if result:
                    access_request.blockchain_approval_tx = result['tx_hash']
                    access_request.save()
            
            messages.success(request, 'Request rejected')
        
        return redirect('data_management:view_requests')
    
    return render(request, 'data_management/process_request.html', {
        'access_request': access_request
    })


from core.models import User
