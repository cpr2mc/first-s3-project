import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')

    def __str__(self):
        return self.name
    
    def get_s3_folder_name(self):
        """
        Returns the S3 folder name for this project
        Format: projects/{project_id}/
        """
        return f"projects/{self.id}/"
    
    @property
    def member_count(self):
        return self.projectmembership_set.count()

class ProjectMembership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='added_members')

    class Meta:
        unique_together = ('project', 'user')
    
    def __str__(self):
        return f"{self.user.username} in {self.project.name}"

class Invitation(models.Model):
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invitation for {self.email}"
    
    def save(self, *args, **kwargs):
        # Set expiration date to 10 days from creation if not already set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=10)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_accepted and not self.is_expired

def get_project_upload_path(instance, filename):
    """
    Generate upload path for files based on project
    """
    return f"projects/{instance.project.id}/{filename}"

class UploadedFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=get_project_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name.split('/')[-1] if self.file else 'No file'

    @property
    def filename(self):
        """Return just the filename without the path"""
        return self.file.name.split('/')[-1] if self.file else ''

    class Meta:
        # Add ordering to show newest files first
        ordering = ['-uploaded_at']
        # Add permission for viewing only own files
        permissions = [
            ("view_own_files", "Can view only their own files"),
        ]
