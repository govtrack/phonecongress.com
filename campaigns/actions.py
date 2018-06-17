from django.template import Template, Context
from django.utils.safestring import mark_safe

import html
import re

from .models import ActionType, Campaign

# CHOOSE THE BEST ACTION FOR A USER

def select_action(actions, user_props):
    # Choose the best Action for a user from this congressional
    # district.
    actions = [x for x in actions if x is not None]
    if len(actions) == 0:
      return None
    actions.sort(key = lambda action : action["priority"])
    return actions[0]

# DYNAMIC CAMPAIGNS

class AutoCampaign:
  def __init__(self, actions):
    self.actions = actions
    self.extra = { }
  def get_action(self, user_props):
    return select_action(
      [func(None, action_spec, user_props)
              for func, action_spec in self.actions],
      user_props)

def get_campaign_from_key(campaign_key):
  # Loads automatic dynamically-generated campaign info.
  m = re.match(r"^congress/bills/[^/]+/(\d+)(?:/(support|oppose))?$", campaign_key)
  if m:
    return campaign_for_bill(int(m.group(1)), m.group(2))
  return None

def campaign_for_bill(govtrack_bill_id, support_oppose):
  try:
    data = load_json_from_url("https://www.govtrack.us/api/v2/bill/%d" % govtrack_bill_id)
  except:
    return None

  if not data["is_alive"]:
    return None

  if not support_oppose:
    return {
      "title": data["title"],
      "campaigns": [
        {
          "key": "support",
          "title": "Support " + data["title"],
        },
        {
          "key": "oppose",
          "title": "Oppose " + data["title"],
        },
      ]
    }
  else:
    ask = (("support " + data["title"])
          if support_oppose == "support"
          else ("oppose " + data["title"]))
    if data["current_chamber"] == "house":
      return AutoCampaign([
          (congress_representative, {
            "cta": "Call your representative to tell them you %s this bill." % support_oppose,
            "ask": ask,
          })])
    if data["current_chamber"] == "senate":
      return AutoCampaign([
          (congress_senators, {
            "cta": "Call your senators to tell them you %s this bill." % support_oppose,
            "ask": ask,
          })])
    return AutoCampaign([])


# ACTION TYPE IMPLEMENTATIONS

def render_commonmark_template(template, context):
  # Render a CommonMark template to HTML.

  # Replace template tags with Unicode sentinels so that
  # the template tags do not impact CommonMark rendering.
  substitutions = []
  import re
  def replace(m):
      # Record the substitution.
      index = len(substitutions)
      substitutions.append(m.group(0))
      return "\uE000%d\uE001" % index # use Unicode private use area code points
  template = re.sub("{%.*?%}|{{.*?}}", replace, template)

  # Render the CommonMark.

  # Prevent CommonMark from mucking with our sentinels
  # in URLs though - it would otherwise add escaping.
  from CommonMark import inlines
  def urlencode_special(uri):
      import urllib.parse
      return "".join(
          urllib.parse.quote(c, safe="/@:+?=&()%#*,") # this is what CommonMark does
          if c not in "\uE000\uE001" else c # but keep our special codes
          for c in uri)
  inlines.normalize_uri = urlencode_special

  # Render.
  import CommonMark
  template = CommonMark.HtmlRenderer().render(CommonMark.Parser().parse(template))

  # Put the template tags back that we removed prior to running
  # the CommonMark renderer.
  def replace(m):
      return substitutions[int(m.group(1))]
  template = re.sub("\uE000(\d+)\uE001", replace, template)

  # And finally render the Django template.
  return Template(template).render(Context(context))

legislator_data = None

def find_legislators(filter_func):
  # Load the congress-legislators/legislators-current YAML data.
  global legislator_data
  if legislator_data is None:
    legislator_data = load_yaml_from_url("https://raw.githubusercontent.com/unitedstates/congress-legislators/master/legislators-current.yaml")
    if legislator_data is None:
      raise ValueError("Null data.")

    # Transform.
    for legislator in legislator_data:
      # only keep current term
      legislator["term"] = legislator["terms"][-1]

      # form a name
      legislator["name"]["full"] = build_legislator_name(legislator, legislator["term"], "full")

  # Run the filter function to yield matching legislators.
  for legislator in legislator_data:
    if filter_func(legislator):
      yield legislator

call_congress_tips = """
  If you have a brief personal story, say it now. Just **one sentence** about
  how this issue affects your life is enough to show the staffer that the
  issue means something to you. It's also **OK** to skip the personal story.

  The staffer may ask for your name and address so that they can make a
  note of your call. After that, just say _Thank you_ and you are done!
  Your goal is to be counted, so a quick and courteous call like this is
  all it takes.

  If you get voicemail, leave your name and address in your message.
"""

def congress_representative(action_type, action, user):
  # Does the user have a representative?
  def find_rep(legislator):
    if action.get("id_in") and legislator["id"] not in action.get("id_in"):
      return False
    if action.get("id_not_in") and legislator["id"] in action.get("id_not_in"):
      return False
    term = legislator['term']
    if     term['type'] == 'rep' \
       and term['state'] == user['cd'][0:2] \
       and term['district'] == int(user['cd'][2:]):
       return True
  reps = list(find_legislators(find_rep))
  if len(reps) != 1:
    return None
  rep = reps[0]

  # Do we have a phone number?
  if not rep["term"].get("phone"):
    return None

  # Render the action body template.
  template = """
  {{intro}}

  {{cta}}

  Here's what you need to do. **Call {{rep.name.full}}
  at {{tel_link}}.** A staff member in the representative's office will
  probably pick up the phone. Say:

  > Hi, I'm a resident of {% firstof user.city "[say the city you live in]" %}
  > and I would like Representative {{rep.name.last}} to {{ask}}.
  """ + call_congress_tips

  return {
    "priority": 441,
    "html": render_commonmark_template(template, {
      "cta": action["cta"],
      "ask": action["ask"],
      "user": user,
      "rep": rep,
      "tel_link": mark_safe("<a href='tel:+1" + html.escape(rep["term"]["phone"]) + "'>" + html.escape(rep["term"]["phone"]) + "</a>")
    })
  }

def congress_senators(action_type, action, user):
  # Does the user have a representative?
  def find_rep(legislator):
    if action.get("id_in") and legislator["id"] not in action.get("id_in"):
      return False
    if action.get("id_not_in") and legislator["id"] in action.get("id_not_in"):
      return False
    term = legislator['term']
    if     term['type'] == 'sen' \
       and term['state'] == user['cd'][0:2]:
       return True
  senators = list(find_legislators(find_rep))
  senators = [s for s in senators if s["term"].get("phone")]
  if len(senators) == 0:
    return None

  # Render the action body template.
  template = """
  {{intro}}

  {{cta}}

  A phone call guide follows for each of your senators.

  {% for senator in senators %}
  ***

  <b>#{{forloop.counter}}: Call {{senator.name.full}}
  at {{senator.tel_link}}.</b>

  A staff member in the senator's office will probably pick up the phone. Say:

  > Hi, I'm a resident of {% firstof user.city "[say the city you live in]" %} and I would like
  > Senator {{senator.name.last}} to {{ask}}.
  """ \
  + call_congress_tips \
  + """
  If you would like to write a letter instead, visit [{{senator.name.last}}&rsquo;s homepage]({{senator.website}})
  and fill out their contact form.
  """ \
  + "\n\n{% endfor %}"

  return {
    "priority": 100,
    "html": render_commonmark_template(template, {
      "intro": action.get("intro"),
      "cta": action["cta"],
      "ask": action["ask"],
      "user": user,
      "senators": [{
        "name": senator["name"],
        "website": senator["term"]["url"],
        "tel_link": mark_safe("<a href='tel:+1" + html.escape(senator["term"]["phone"]) + "'>" + html.escape(senator["term"]["phone"]) + "</a>")
      }
      for senator in senators]
    })
  }

def congress_rep_and_senators(action_type, action, user):
  # Does the user have a representative?
  def find_rep(legislator):
    if action.get("id_in") and legislator["id"] not in action.get("id_in"):
      return False
    if action.get("id_not_in") and legislator["id"] in action.get("id_not_in"):
      return False
    term = legislator['term']
    if     term['type'] == 'rep' \
       and term['state'] == user['cd'][0:2] \
       and term['district'] == int(user['cd'][2:]):
       return True
    if     term['type'] == 'sen' \
       and term['state'] == user['cd'][0:2]:
       return True
  legislators = list(find_legislators(find_rep))
  if len(legislators) == 0:
    return None
  legislators.sort(key = lambda x : x["term"]["type"]) # group senators together

  # Render the action body template.
  template = """
  {{cta}}

  Here are the phone numbers for your representative and senators. Information about
  how to call is below.

  {% for legislator in legislators %}<b>#{{forloop.counter}}: {{legislator.name.full}}'s
  DC office phone number is {{legislator.tel_link}}.</b>

  {% endfor %}

  When you call each, a staff member will probably pick up the phone. Then say:

  > Hi, I'm a resident of {% firstof user.city "[say the city you live in]" %}
  > and I would like the [senator or representative] to {{ask}}.
  """ \
  + call_congress_tips

  return {
    "priority": 100,
    "html": render_commonmark_template(template, {
      "cta": action["cta"],
      "ask": action["ask"],
      "user": user,
      "legislators": [{
        "name": legislator["name"],
        "tel_link": mark_safe("<a href='tel:+1" + html.escape(legislator["term"]["phone"]) + "'>" + html.escape(legislator["term"]["phone"]) + "</a>")
      }
      for legislator in legislators]
    })
  }

## LEGISLATIVE UTILS

def build_legislator_name(p, t, mode):
  # Based on:
  # https://github.com/govtrack/govtrack.us-web/blob/master/person/name.py

  # First name.
  firstname = p['name']['first']
  if firstname.endswith('.'):
    firstname = p['name']['middle']
  if p['name'].get('nickname') and len(p['name']['nickname']) < len(firstname):
      firstname = p['name']['nickname']

  # Last name.
  lastname = p['name']['last']
  if p['name'].get('suffix'):
    lastname += ' ' + p['name']['suffix']

  # Title.
  if t['type'] == "sen":
    title = "Sen."
  elif t['state'] == "PR":
    # Puerto Rico's delegate is a Resident Commissioner. Currently delegates
    # have no real voting privileges, so we may not need this, but we'll
    # include for completeness.
    title = "Commish"
  elif t['state'] in ('AS', 'DC', 'GU', 'MP', 'VI'):
    # The delegates.
    title = "Del."
  else:
    # Normal representatives.
    title = "Rep."

  # Role info.
  # Using an en dash to separate the party from the state
  # and a U+2006 SIX-PER-EM SPACE to separate state from
  # district. Will that appear ok/reasonable?
  if t.get('district') in (None, 0):
    role = " (%s–%s)" % (t['party'][0], t['state'])
  else:
    role = " (%s–%s %d)" % (t['party'][0], t['state'], t['district'])

  if mode == "full":
    return title + ' ' + firstname + ' ' + lastname + role
  elif mode == "sort":
    return lastname + ', ' + firstname + ' (' + title + ')' + role
  else:
    raise ValueError(mode)

## HTTP UTILS

def load_json_from_url(url):
  import requests, json
  r = requests.get(url)
  r = json.loads(r.content.decode("utf8"))
  return r

def load_yaml_from_url(url):
  import requests, rtyaml
  r = requests.get(url)
  r = rtyaml.load(r.content)
  return r

