from django.conf.urls import url
from django.contrib import admin

import campaigns.views

urlpatterns = [
	url(r'^$', campaigns.views.homepage),
	url(r'^_geocode$', campaigns.views.geocode),
    url(r'^admin/', admin.site.urls),
]
