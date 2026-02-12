from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random
import string

class User(AbstractUser):
    """Extended User model with blockchain and role information"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    wallet_address = models.CharField(max_length=42, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    two_factor_enabled = models.BooleanField(default=True)
    totp_secret = models.CharField(max_length=32, blank=True, null=True)
    is_mfa_setup = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def is_admin(self):
        return self.role == 'admin'


class OTPToken(models.Model):
    """Model to store OTP tokens for two-factor authentication"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_tokens')
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50, default='login')  # login, data_access, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'core_otp_token'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.user.username} - {self.purpose}"
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Mark OTP as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()


class LoginAttempt(models.Model):
    """Track login attempts for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='login_attempts')
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    failure_reason = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        db_table = 'core_login_attempt'
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.username} - {status} at {self.timestamp}"
