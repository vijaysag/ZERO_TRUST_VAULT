from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from core.models import User, OTPToken, LoginAttempt
from core.services import OTPService, WalletService, TOTPService
import json


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["GET", "POST"])
def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            phone_number = request.POST.get('phone_number', '')
            role = request.POST.get('role', 'user')  # Default to user if not provided
            
            # Validation
            if not all([username, email, password, password_confirm]):
                messages.error(request, 'Passwords do not match')
                return render(request, 'core/register.html', {'hide_sidebar': True})
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return render(request, 'core/register.html', {'hide_sidebar': True})
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return render(request, 'core/register.html', {'hide_sidebar': True})
            
            # Create user
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                    phone_number=phone_number,
                    two_factor_enabled=True
                )
                
                # Proactive wallet assignment (can be skipped if user wants to do it later from profile)
                # But as per request "Whenever user is registered there is pop that wallet is not assigned"
                # This implies we might NOT assign it here to show the pop-up or at least give the choice.
                # Let's keep it proactive but if it fails, the popup will handle it.
                WalletService.assign_wallet_to_user(user)
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'core/register.html', {'hide_sidebar': True})
    
    return render(request, 'core/register.html', {'hide_sidebar': True})


@login_required
@require_http_methods(["POST"])
def toggle_2fa(request):
    """Toggle 2FA state from profile"""
    user = request.user
    user.two_factor_enabled = not user.two_factor_enabled
    user.save()
    status = "enabled" if user.two_factor_enabled else "disabled"
    messages.success(request, f'Two-factor authentication {status} successfully.')
    return redirect('profile')


@login_required
@require_http_methods(["POST"])
def register_blockchain(request):
    """Register user on blockchain from profile (Supports MetaMask)"""
    user = request.user
    if user.wallet_address:
        messages.info(request, 'Already registered on blockchain.')
        return redirect('profile')
    
    # Check if wallet address was provided via MetaMask (POST)
    wallet_address = request.POST.get('wallet_address')
    
    if not wallet_address:
        # Fallback to Ganache auto-assignment if no address provided
        wallet_address = WalletService.assign_wallet_to_user(user)
    else:
        # Save the provided MetaMask address
        user.wallet_address = wallet_address
        user.save()
    
    if wallet_address:
        messages.success(request, f'Successfully registered on blockchain! Wallet: {wallet_address}')
    else:
        messages.error(request, 'Blockchain registration failed. Please ensure your wallet is connected.')
    
    return redirect('profile')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view with mandatory Authenticator MFA"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Credentials correct, check MFA
            request.session['mfa_user_id'] = user.id
            
            if not user.is_mfa_setup:
                # Force MFA setup
                return redirect('mfa_setup')
            else:
                # Require MFA verification
                return redirect('mfa_verify')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'core/login.html', {'hide_sidebar': True})
    
    return render(request, 'core/login.html', {'hide_sidebar': True})


def mfa_setup(request):
    """Initial TOTP setup view with QR code"""
    user_id = request.session.get('mfa_user_id')
    if not user_id:
        return redirect('login')
    
    user = User.objects.get(id=user_id)
    if user.is_mfa_setup:
        return redirect('login')
    
    # Get or generate secret
    secret = request.session.get('mfa_secret')
    if not secret:
        secret = TOTPService.generate_secret()
        request.session['mfa_secret'] = secret
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        
        if TOTPService.verify_totp(secret, otp_code):
            user.totp_secret = secret
            user.is_mfa_setup = True
            user.save()
            
            # Now complete the login with explicit backend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Clean up session
            del request.session['mfa_user_id']
            del request.session['mfa_secret']
            
            messages.success(request, "Authenticator linked successfully!")
            return redirect('access_control:user_dashboard')
        else:
            messages.error(request, "Invalid code. Please ensure your app is synced and try again.")
    
    provisioning_uri = TOTPService.get_provisioning_uri(user, secret)
    qr_code = TOTPService.generate_qr_code(provisioning_uri)
    
    return render(request, 'core/mfa_setup.html', {
        'qr_code': qr_code,
        'secret': secret,
        'hide_sidebar': True
    })


def mfa_verify(request):
    """Verify 6-digit TOTP code during login"""
    user_id = request.session.get('mfa_user_id')
    if not user_id:
        return redirect('login')
    
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        
        # Add small window of drift (valid for current and previous 30s)
        if TOTPService.verify_totp(user.totp_secret, otp_code):
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            del request.session['mfa_user_id']
            
            if user.is_admin():
                return redirect('data_management:admin_dashboard')
            return redirect('access_control:user_dashboard')
        else:
            messages.error(request, "Invalid verification code.")
    
    return render(request, 'core/mfa_verify.html', {'user': user, 'hide_sidebar': True})


@login_required
def logout_view(request):
    """User logout view"""
    username = request.user.username
    logout(request)
    messages.success(request, f'Goodbye, {username}!')
    return redirect('login')


@login_required
def profile_view(request):
    """User profile view"""
    return render(request, 'core/profile.html', {
        'user': request.user
    })


# API endpoints for AJAX requests
@csrf_exempt
@require_http_methods(["POST"])
def resend_otp_api(request):
    """API endpoint to resend OTP"""
    try:
        user_id = request.session.get('pending_user_id')
        if not user_id:
            return JsonResponse({'success': False, 'error': 'No pending login'}, status=400)
        
        user = User.objects.get(id=user_id)
        OTPService.generate_otp(user, purpose='login')
        
        return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
