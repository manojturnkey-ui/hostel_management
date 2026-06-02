from django.contrib.auth.models import AbstractUser
from django.db import models

from config.validators import validate_mobile_number


class User(AbstractUser):
    display_name = models.CharField(max_length=150, blank=True)
    mobile_number = models.CharField(max_length=10, blank=True, validators=[validate_mobile_number])

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return self.display_name or self.get_full_name() or self.username

    @property
    def panel_name(self) -> str:
        return self.display_name or self.first_name or self.username
