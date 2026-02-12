from django.db import models
from django.conf import settings
from django.utils import timezone
import os
import uuid

def data_file_path(instance, filename):
    """Generate file path for uploaded data files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('data_files', str(instance.uploaded_by.id), filename)


class DataFile(models.Model):
    """Model to store uploaded data files"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ]
    
    data_id = models.CharField(max_length=100, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=data_file_path)
    file_type = models.CharField(max_length=10)
    file_size = models.BigIntegerField()  # in bytes
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)  # Transaction hash from blockchain
    ipfs_hash = models.CharField(max_length=100, blank=True, null=True)  # For future IPFS integration
    
    class Meta:
        db_table = 'data_file'
        ordering = ['-uploaded_at']
        verbose_name = 'Data File'
        verbose_name_plural = 'Data Files'
    
    def __str__(self):
        return f"{self.title} ({self.data_id})"
    
    def save(self, *args, **kwargs):
        if not self.data_id:
            self.data_id = f"DATA-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        return self.file.name.split('.')[-1].lower()
    
    def is_active(self):
        return self.status == 'active'


class DataModificationLog(models.Model):
    """Log all modifications to data files"""
    ACTION_CHOICES = [
        ('upload', 'Upload'),
        ('modify', 'Modify'),
        ('delete', 'Delete'),
        ('restore', 'Restore'),
    ]
    
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='modification_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)
    
    class Meta:
        db_table = 'data_modification_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} on {self.data_file.title} by {self.performed_by.username}"
