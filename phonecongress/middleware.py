from django.conf import settings

def global_template_context(request):
    return {
        "GOOGLE_ANALYTICS_ID": settings.GOOGLE_ANALYTICS_ID
    }
