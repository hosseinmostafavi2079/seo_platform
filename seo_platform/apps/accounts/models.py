from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_super_admin = models.BooleanField(
        default=False, 
        help_text="Designates whether this user has full access to all sites and settings."
    )

    def __str__(self):
        return self.username