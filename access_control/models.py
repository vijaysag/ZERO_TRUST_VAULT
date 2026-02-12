from django.db import models
from django.conf import settings
from django.utils import timezone
from data_management.models import DataFile


class AccessRequest(models.Model):
    """Model to store user requests for data access"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('accessed', 'Accessed'),
    ]
    
    request_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_requests')
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='access_requests')
    reason = models.TextField(help_text="Reason for requesting access")
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Admin response
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_requests'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    # OTP for data access
    access_otp_sent = models.BooleanField(default=False)
    access_granted_at = models.DateTimeField(null=True, blank=True)
    
    # Blockchain tracking
    blockchain_request_tx = models.CharField(max_length=66, blank=True, null=True)
    blockchain_approval_tx = models.CharField(max_length=66, blank=True, null=True)
    blockchain_access_tx = models.CharField(max_length=66, blank=True, null=True)
    
    class Meta:
        db_table = 'access_request'
        ordering = ['-requested_at']
        verbose_name = 'Access Request'
        verbose_name_plural = 'Access Requests'
    
    def __str__(self):
        return f"Request #{self.request_id} - {self.user.username} for {self.data_file.title}"
    
    def is_pending(self):
        return self.status == 'pending'
    
    def is_approved(self):
        return self.status == 'approved'
    
    def approve(self, admin_user, notes=''):
        """Approve the access request"""
        self.status = 'approved'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.admin_notes = notes
        self.save()
    
    def reject(self, admin_user, notes=''):
        """Reject the access request"""
        self.status = 'rejected'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.admin_notes = notes
        self.save()
    
    def mark_as_accessed(self):
        """Mark request as accessed after OTP verification"""
        self.status = 'accessed'
        self.access_granted_at = timezone.now()
        self.save()


class DataAccessLog(models.Model):
    """Log all data access events"""
    ACCESS_TYPE_CHOICES = [
        ('view', 'View'),
        ('download', 'Download'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_logs')
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='access_logs')
    access_request = models.ForeignKey(AccessRequest, on_delete=models.CASCADE, related_name='access_logs', null=True)
    access_type = models.CharField(max_length=10, choices=ACCESS_TYPE_CHOICES, default='view')
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)
    
    class Meta:
        db_table = 'data_access_log'
        ordering = ['-accessed_at']
        verbose_name = 'Data Access Log'
        verbose_name_plural = 'Data Access Logs'
    
    def __str__(self):
        return f"{self.user.username} accessed {self.data_file.title} at {self.accessed_at}"
