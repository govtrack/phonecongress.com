from django.db import models
from django.contrib.auth.models import AbstractUser

from jsonfield import JSONField

class Campaign(models.Model):
	"""A Campaign is a call to action for users. Each user can participate in a Campaign just once."""

    owner = models.ForeignKey(User, related_name="campaigns", help_text="The User that owns the Campaign.")
    title = models.CharField(max_length=128, help_text="The display name of the Campaign.")
    active = models.BooleanField(default=False, help_text="Whether this campaign is currently running.")

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)
    extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

class ActionType(models.Model):
	"""A type of Action that a user can take. ActionTypes are immutable since they are associated with Actions that users have taken."""

    owner = models.ForeignKey(User, related_name="campaigns", help_text="The User that created the ActionType.")
    title = models.CharField(max_length=128, help_text="The display name of the ActionType.")

    specification = JSONField(blank=True, default={}, help_text="Data on what this ActionType is actually about.")

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)
    extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

class Action(models.Model):
	"""An Action is a particular activity a user can take when taking action for a Campaign. Actions segment users. They should not be modified once users have taken action on them."""

    campaign = models.ForeignKey(Campaign, related_name="actions", help_text="The Campaign that this Action is a part of.")
    title = models.CharField(max_length=128, help_text="A brief summary of the Action.")
    action_type = models.ForeignKey(ActionType, related_name="actions", help_text="The ActionType that specifies what sort of action this is.")

    specification = JSONField(blank=True, default={}, help_text="Data that is interpreted by the ActionType for generating call scripts, etc.")

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)
    extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

class UserAction(models.Model):
	"""A UserAction records when a User has taken an Action"""

    user = models.ForeignKey(User, related_name="actions", help_text="The User that took this action.")
    action = models.ForeignKey(Action, related_name="useractions", help_text="The Action that was taken.")

    details = JSONField(blank=True, default={}, help_text="Data that is filled in by the ActionType for generating call scripts, etc.")
    state = models.CharField(blank=True, null=True, max_length=16, help_text="The status of the Action.")

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)
    extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")
