from django.contrib import admin

from .models import Campaign, ActionType, Action

class CampaignAdmin(admin.ModelAdmin):
	list_display = ('title', 'owner', 'active', 'created')

class ActionTypeAdmin(admin.ModelAdmin):
	list_display = ('title', 'owner', 'created')

class ActionAdmin(admin.ModelAdmin):
	list_display = ('title', 'campaign', 'action_type', 'created')
	raw_id_fields = ('action_type', 'campaign',)


admin.site.register(Campaign, CampaignAdmin)
admin.site.register(ActionType, ActionTypeAdmin)
admin.site.register(Action, ActionAdmin)
