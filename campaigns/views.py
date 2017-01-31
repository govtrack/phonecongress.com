from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt

import json

state_apportionment = {'AL': 7, 'AK': 1, 'AS': 'T', 'AZ': 9, 'AR': 4, 'CA': 53, 'CO': 7, 'CT': 5, 'DE': 1, 'DC': 'T', 'FL': 27, 'GA': 14, 'GU': 'T', 'HI': 2, 'ID': 2, 'IL': 18, 'IN': 9, 'IA': 4, 'KS': 4, 'KY': 6, 'LA': 6, 'ME': 2, 'MD': 8, 'MA': 9, 'MI': 14, 'MN': 8, 'MS': 4, 'MO': 8, 'MT': 1, 'NE': 3, 'NV': 4, 'NH': 2, 'NJ': 12, 'NM': 3, 'NY': 27, 'NC': 13, 'ND': 1, 'MP': 'T', 'OH': 16, 'OK': 5, 'OR': 5, 'PA': 18, 'PR': 'T', 'RI': 2, 'SC': 7, 'SD': 1, 'TN': 9, 'TX': 36, 'UT': 4, 'VT': 1, 'VI': 'T', 'VA': 11, 'WA': 10, 'WV': 3, 'WI': 8, 'WY': 1}
state_names = {"AL":"Alabama", "AK":"Alaska", "AS":"American Samoa", "AZ":"Arizona", "AR":"Arkansas", "CA":"California", "CO":"Colorado", "CT":"Connecticut", "DE":"Delaware", "DC":"District of Columbia", "FL":"Florida", "GA":"Georgia", "GU":"Guam", "HI":"Hawaii", "ID":"Idaho", "IL":"Illinois", "IN":"Indiana", "IA":"Iowa", "KS":"Kansas", "KY":"Kentucky", "LA":"Louisiana", "ME":"Maine", "MD":"Maryland", "MA":"Massachusetts", "MI":"Michigan", "MN":"Minnesota", "MS":"Mississippi", "MO":"Missouri", "MT":"Montana", "NE":"Nebraska", "NV":"Nevada", "NH":"New Hampshire", "NJ":"New Jersey", "NM":"New Mexico", "NY":"New York", "NC":"North Carolina", "ND": "North Dakota", "MP":"Northern Mariana Islands", "OH":"Ohio", "OK":"Oklahoma", "OR":"Oregon", "PA":"Pennsylvania", "PR":"Puerto Rico", "RI":"Rhode Island", "SC":"South Carolina", "SD":"South Dakota", "TN":"Tennessee", "TX":"Texas", "UT":"Utah", "VT":"Vermont", "VI":"Virgin Islands", "VA":"Virginia", "WA":"Washington", "WV":"West Virginia", "WI":"Wisconsin", "WY":"Wyoming", "DK": "Dakota Territory", "PI": "Philippines", "OL": "Territory of Orleans"}

from .models import Campaign
from .actions import get_campaign_from_key

def homepage(request):
  active_campaigns = list(Campaign.objects.filter(active=True))
  active_campaigns.sort(key = lambda c : (c.extra.get("priority") or 0, c.created))
  return render(request, "index.html", { 'campaigns': active_campaigns })

def auto_campaign(request, campaign_key):
  campaign = get_campaign_from_key(campaign_key)
  if not campaign: raise Http404()
  return render(request, "index.html", {
    'title': campaign['title'],
    'campaign_key': campaign_key,
    'campaigns': [{
      'id': c['key'],
      'title': c['title'],
    }
    for c in campaign["campaigns"]],
  })

@csrf_exempt
def geocode(request):
  from geocodio import GeocodioClient
  from geocodio.exceptions import GeocodioDataError

  # HACK
  from geocodio.client import ALLOWED_FIELDS
  ALLOWED_FIELDS.append("cd115")
  # HACK

  # Look up address or coordinate.

  client = GeocodioClient(settings.GEOCODIO_API_KEY)
  try:
    if "address" in request.POST:
      info = client.geocode(request.POST["address"],
        fields=["cd115"])
    
    elif "latitude" in request.POST:
      info = client.reverse_point(float(request.POST["latitude"]), float(request.POST.get("longitude", "")),
        fields=["cd115"])
    
    else:
      return JsonResponse({'status':'error', 'message': 'invalid query'})
    
    result = info["results"][0]
  
  except (ValueError, GeocodioDataError, IndexError):
    return JsonResponse({'status':'error', 'message': 'The location was not understood.'})

  # Extract fields from result.

  coord = result["location"]
  address = result["formatted_address"]
  state = result["address_components"].get("state")
  if state not in state_apportionment:
    return JsonResponse({'status':'error', 'message': 'The location does not seem to be in the United States.'})
  if "fields" not in result:
    return JsonResponse({'status':'error', 'message': 'We could not determine the congressional district for that location.'})
  dist = result["fields"]["congressional_district"]["district_number"]
  if dist in (98, 99): dist = 0
  if (state_apportionment[state] in ("T", 1) and dist != 0) \
   or (state_apportionment[state] not in ("T", 1) and not (1 <= dist <= state_apportionment[state])):
    raise ValueError("Hmm. We got back invalid data. " + repr(request.POST) + " -- " + repr(info))
  cd = "%s%02d" % (state, dist)

  # Return.

  return JsonResponse({
    'status': 'ok',
    'coord': coord,
    'address': address,
    'city': result["address_components"].get("city"),
    'cd': cd,
    'state': state_names[state],
    'district_html': ordinal_html(dist) if dist > 0 else "At Large",
    })

def ordinal_html(value):
    """
    Converts an integer to its ordinal as HTML. 1 is '1<sup>st</sup>',
    and so on.
    """
    try:
        value = int(value)
    except ValueError:
        return value
    from django.utils.translation import ugettext as _
    t = (_('th'), _('st'), _('nd'), _('rd'), _('th'), _('th'), _('th'), _('th'), _('th'), _('th'))
    if value % 100 in (11, 12, 13): # special case
        return "%d<sup>%s</sup>" % (value, t[0])
    return '%d<sup>%s</sup>' % (value, t[value % 10])

@csrf_exempt
def get_action(request):
  # Get the campaign.
  try:
    campaign = get_campaign_from_key(request.POST.get("campaign", ""))
    if not campaign:
      campaign = Campaign.objects.get(active=True, id=request.POST.get("campaign"))
    user = json.loads(request.POST["user"])
  except:
    return JsonResponse({'status':'error', 'message': 'Invalid parameters.'})

  # Determine if any Action for this Campaign applies,
  # and choose the one that is most specific if the Action
  # applies.
  action = campaign.get_action(user)
  if action is None :
    return JsonResponse({'status':'error', 'message':
      campaign.extra.get("no-action-message") or
      'We do not have any actions you can take for that topic. Sorry!!'})

  return JsonResponse(action)
