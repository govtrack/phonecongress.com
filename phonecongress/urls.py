from django.conf.urls import url
from django.contrib import admin

import campaigns.views

urlpatterns = [
	url(r'^$', campaigns.views.homepage),
	url(r'^topic/(.*)$', campaigns.views.auto_campaign),
	url(r'^_geocode$', campaigns.views.geocode),
	url(r'^_action$', campaigns.views.get_action),
    url(r'^admin/', admin.site.urls),
]
