from django.db import models
from django.contrib.auth.models import AbstractUser

from jsonfield import JSONField

class User(AbstractUser):
    """A registered user."""

    us_congressional_district = models.CharField(max_length=4, help_text="The U.S. congressional district that the user lives in, in XX## format.")

    extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")
