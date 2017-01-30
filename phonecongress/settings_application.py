from .settings import *

INSTALLED_APPS += [
	"campaigns"
]

TEMPLATES[0]['OPTIONS']['context_processors'].append('phonecongress.middleware.global_template_context')

GOOGLE_ANALYTICS_ID = environment.get('ga')
GEOCODIO_API_KEY = environment.get('geocodio')
