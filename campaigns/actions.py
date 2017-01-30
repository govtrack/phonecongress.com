from django.template import Template, Context
from django.utils.safestring import mark_safe
import html

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

def load_yaml_from_url(url):
  import requests, rtyaml
  r = requests.get(url)
  r = rtyaml.load(r.content)
  return r

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

def congress_representative(action_type, action, user):
  # Does the user have a representative?
  def find_rep(legislator):
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
  return {
    "priority": 441,
    "title": action["title"],
    "html": render_commonmark_template(action["body"], {
      "user": user,
      "rep": rep,
      "rep_name": rep["name"]["full"],
      "tel_link": mark_safe("<a href='tel:+1" + html.escape(rep["term"]["phone"]) + "'>" + html.escape(rep["term"]["phone"]) + "</a>")
    })
  }

def congress_senators(action_type, action, user):
  # Does the user have a representative?
  def find_rep(legislator):
    term = legislator['term']
    if     term['type'] == 'sen' \
       and term['state'] == user['cd'][0:2]:
       return True
  senators = list(find_legislators(find_rep))
  senators = [s for s in senators if s["term"].get("phone")]
  if len(senators) == 0:
    return None

  # Render the action body template.
  template = Template(action["body"])
  return {
    "priority": 100,
    "title": action["title"],
    "html": render_commonmark_template(action["body"], {
      "user": user,
      "senators": [{
        "name": senator["name"],
        "tel_link": mark_safe("<a href='tel:+1" + html.escape(senator["term"]["phone"]) + "'>" + html.escape(senator["term"]["phone"]) + "</a>")
      }
      for senator in senators]
    })
  }

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

