from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    Company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='branches')
    
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_branches'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('Company', 'name')

    def __str__(self):
        return f"{self.Company.name} - {self.name}"
    

class CompanyInvite(models.Model):
    Company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='invites')
    
    email = models.EmailField()
    role = models.CharField(max_length=20)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    def __str__(self):
        return f"Invite for {self.email} to join {self.Company.name} as {self.role}"
        