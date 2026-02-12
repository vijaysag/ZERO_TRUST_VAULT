from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.models import OTPToken
import random
import string


import pyotp
import qrcode
import io
import base64


class TOTPService:
    """Service to handle Authenticator App (TOTP) MFA"""
    
    @staticmethod
    def generate_secret():
        """Generate a random base32 secret for TOTP"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_provisioning_uri(user, secret):
        """Get the URI for scanning into Authenticator Apps"""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="ZeroTrustVault"
        )
    
    @staticmethod
    def generate_qr_code(provisioning_uri):
        """Generate a base64 encoded QR code image"""
        img = qrcode.make(provisioning_uri)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    @staticmethod
    def verify_totp(secret, code):
        """Verify the 6-digit TOTP code (Allows 30s drift)"""
        totp = pyotp.totp.TOTP(secret)
        return totp.verify(code, valid_window=1)


class OTPService:
    """Service to handle OTP generation and verification"""
    
    @staticmethod
    def generate_otp(user, purpose='login'):
        """Generate and send OTP to user"""
        # Generate OTP
        otp_code = OTPToken.generate_otp()
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        # Create OTP token
        otp_token = OTPToken.objects.create(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )
        
        # Send OTP via email
        OTPService.send_otp_email(user, otp_code, purpose)
        
        return otp_token
    
    @staticmethod
    def send_otp_email(user, otp_code, purpose='login'):
        """Send OTP via email"""
        subject = f'Your OTP for {purpose.replace("_", " ").title()}'
        
        message = f"""
        Hello {user.username},
        
        Your One-Time Password (OTP) is: {otp_code}
        
        This OTP will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
        
        Purpose: {purpose.replace('_', ' ').title()}
        
        If you did not request this OTP, please ignore this email.
        
        Best regards,
        Blockchain Data Vault Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            print(f"OTP sent to {user.email}: {otp_code}")  # For development
            return True
        except Exception as e:
            print(f"Error sending OTP email: {str(e)}")
            return False
    
    @staticmethod
    def verify_otp(user, otp_code, purpose='login'):
        """Verify OTP code"""
        try:
            otp_token = OTPToken.objects.filter(
                user=user,
                otp_code=otp_code,
                purpose=purpose,
                is_used=False
            ).latest('created_at')
            
            if otp_token.is_valid():
                otp_token.mark_as_used()
                return True
            else:
                return False
        except OTPToken.DoesNotExist:
            return False
    
    @staticmethod
    def cleanup_expired_otps():
        """Delete expired OTP tokens"""
        OTPToken.objects.filter(
            expires_at__lt=timezone.now(),
            is_used=False
        ).delete()


class WalletService:
    """Service to manage blockchain wallet addresses"""
    
    @staticmethod
    def assign_wallet_to_user(user):
        """Assign a unique wallet address to user"""
        from blockchain.services import blockchain_service
        from core.models import User
        
        # Get count of existing users with wallets
        user_count = User.objects.exclude(wallet_address__isnull=True).count()
        
        # Assign next available wallet (skip index 0 as it's admin)
        wallet_address = blockchain_service.assign_wallet_address(user_count + 1)
        
        if wallet_address:
            user.wallet_address = wallet_address
            user.save()
            return wallet_address
        
        return None
