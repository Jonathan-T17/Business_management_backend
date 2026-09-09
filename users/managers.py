from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email,full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user
    

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        from core.roles import Roles

        extra_fields["role"] = Roles.SUPERUSER
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_active"] = True
        extra_fields["email_verified"] = True
        extra_fields["account_state"] = "ACTIVE"
        extra_fields["company"] = None
        extra_fields["branch"] = None

        if not password:
            raise ValueError("Platform superusers require a password.")
        return self.create_user(email, full_name, password, **extra_fields)