from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager
from django.utils import timezone

# Create your models here.
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('SUPERUSER', 'Superuser'),
        ('ADMIN', 'Company Admin'),
        ('MANAGER', 'Branch Manager'),
        ('EMPLOYEE', 'Employee'),
        ('INDIVIDUAL', 'Individual'),
    )

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='INDIVIDUAL')
    
    company = models.ForeignKey(
        'companies.Company', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users')
    
    branch = models.ForeignKey(
        'companies.Branch', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users')
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    def __str__(self):
        return self.email
    



    # def save(self, *args, **kwargs):
    #     # Automatically grant admin-site access
    #     if self.role in ['SUPERUSER', 'ADMIN']:
    #         self.is_staff = True
    #     super().save(*args, **kwargs)