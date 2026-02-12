from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from data_management.models import DataFile
from access_control.models import AccessRequest, DataAccessLog
from core.models import User
from core.services import OTPService, TOTPService
from blockchain.services import blockchain_service


def is_regular_user(user):
    """Check if user is a regular user (not admin)"""
    return user.is_authenticated and not user.is_admin()


@login_required
def user_dashboard(request):
    """User dashboard view"""
    # Get user's statistics
    my_requests = AccessRequest.objects.filter(user=request.user)
    pending_count = my_requests.filter(status='pending').count()
    approved_count = my_requests.filter(status='approved').count()
    accessed_count = my_requests.filter(status='accessed').count()
    
    # Recent requests
    recent_requests = my_requests.select_related('data_file').order_by('-requested_at')[:10]
    
    # Available data files
    available_files = DataFile.objects.filter(status='active').count()
    
    context = {
        'pending_count': pending_count,
        'approved_count': approved_count,
        'accessed_count': accessed_count,
        'available_files': available_files,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'access_control/user_dashboard.html', context)


@login_required
def browse_data(request):
    """Browse available data files"""
    files = DataFile.objects.filter(status='active').order_by('-uploaded_at')
    
    # Check which files user has already requested
    user_requests = AccessRequest.objects.filter(
        user=request.user
    ).values_list('data_file_id', flat=True)
    
    return render(request, 'access_control/browse_data.html', {
        'files': files,
        'user_requests': list(user_requests)
    })


@login_required
def request_data_access(request, data_id):
    """Request access to a data file"""
    data_file = get_object_or_404(DataFile, data_id=data_id, status='active')
    
    # Check if user already has a pending or approved request
    existing_request = AccessRequest.objects.filter(
        user=request.user,
        data_file=data_file,
        status__in=['pending', 'approved']
    ).first()
    
    if existing_request:
        messages.warning(request, 'You already have a pending or approved request for this file')
        return redirect('access_control:my_requests')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Please provide a reason for your request')
            return render(request, 'access_control/request_data_access.html', {'data_file': data_file})
        
        try:
            # Create access request
            access_request = AccessRequest.objects.create(
                user=request.user,
                data_file=data_file,
                reason=reason,
                status='pending'
            )
            
            # Record on blockchain
            if blockchain_service.contract:
                result = blockchain_service.create_access_request(
                    request.user.wallet_address or request.user.username,
                    request.user.username,
                    data_file.data_id,
                    data_file.title
                )
                
                if result:
                    access_request.blockchain_request_tx = result['tx_hash']
                    access_request.save()
            
            messages.success(request, 'Access request submitted successfully! Waiting for admin approval.')
            return redirect('access_control:my_requests')
            
        except Exception as e:
            messages.error(request, f'Request failed: {str(e)}')
    
    return render(request, 'access_control/request_data_access.html', {'data_file': data_file})


@login_required
def my_requests(request):
    """View user's access requests"""
    requests_list = AccessRequest.objects.filter(
        user=request.user
    ).select_related('data_file', 'processed_by').order_by('-requested_at')
    
    return render(request, 'access_control/my_requests.html', {
        'requests': requests_list
    })


@login_required
def view_data_with_otp(request, request_id):
    """View data after OTP verification"""
    access_request = get_object_or_404(
        AccessRequest,
        request_id=request_id,
        user=request.user,
        status='approved'
    )
    
    if request.method == 'POST':
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Show OTP form
            return render(request, 'access_control/view_data_with_otp.html', {
                'access_request': access_request,
                'step': 2
            })
        
        elif step == '2':
            # Step 2: Verify TOTP from Authenticator App and show data
            otp_code = request.POST.get('otp_code')
            
            if TOTPService.verify_totp(request.user.totp_secret, otp_code):
                # TOTP verified, grant access
                access_request.mark_as_accessed()
                
                # Log access
                access_log = DataAccessLog.objects.create(
                    user=request.user,
                    data_file=access_request.data_file,
                    access_request=access_request,
                    access_type='view',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Record on blockchain
                if blockchain_service.contract:
                    result = blockchain_service.log_data_access(
                        request.user.wallet_address or request.user.username,
                        request.user.username,
                        access_request.data_file.data_id,
                        'view'
                    )
                    
                    if result:
                        access_log.blockchain_tx_hash = result['tx_hash']
                        access_log.save()
                        
                        access_request.blockchain_access_tx = result['tx_hash']
                        access_request.save()
                
                messages.success(request, 'Access granted! Authenticator verified.')
                return render(request, 'access_control/view_data_with_otp.html', {
                    'access_request': access_request,
                    'step': 3,
                    'data_file': access_request.data_file
                })
            else:
                messages.error(request, 'Invalid identification code. Please check your Authenticator app.')
                return render(request, 'access_control/view_data_with_otp.html', {
                    'access_request': access_request,
                    'step': 2
                })
    
    return render(request, 'access_control/view_data_with_otp.html', {
        'access_request': access_request,
        'step': 1
    })


@login_required
def download_data(request, request_id):
    """Download data file after verification"""
    access_request = get_object_or_404(
        AccessRequest,
        request_id=request_id,
        user=request.user,
        status='accessed'  # Must have already accessed
    )
    
    try:
        data_file = access_request.data_file
        
        # Log download
        access_log = DataAccessLog.objects.create(
            user=request.user,
            data_file=data_file,
            access_request=access_request,
            access_type='download',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Record on blockchain
        if blockchain_service.contract:
            result = blockchain_service.log_data_access(
                request.user.wallet_address or request.user.username,
                request.user.username,
                data_file.data_id,
                'download'
            )
            
            if result:
                access_log.blockchain_tx_hash = result['tx_hash']
                access_log.save()
        
        # Serve file
        response = FileResponse(data_file.file.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{data_file.file.name.split("/")[-1]}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Download failed: {str(e)}')
        return redirect('access_control:my_requests')


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


# API endpoint for resending OTP
@require_http_methods(["POST"])
@login_required
def resend_data_access_otp(request):
    """Resend OTP for data access"""
    try:
        OTPService.generate_otp(request.user, purpose='data_access')
        return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
