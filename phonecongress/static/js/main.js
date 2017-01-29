// Put footer at the bottom.
$('#body').css({
  minHeight: $(window).height() - $('header').outerHeight() - $('footer').outerHeight() - 1
});

$('#use-my-address').click(function() {
  if (!("geolocation" in navigator)) {
    alert("Location is not available.");
    return;
  }
  navigator.geolocation.getCurrentPosition(function(position) {
    geocode({
      longitude: position.coords.longitude,
      latitude: position.coords.latitude
      });
  });
})

function geocode(data, go_next) {
  ajax_with_indicator({
    method: "POST",
    url: "/_geocode",
    data: data,
    success: function(res) {
      localStorage.setItem('geocode', JSON.stringify(res));
      onHasGeocode(res);
      if (go_next)
        onTopicSubmit();
    }
  })
}

$(function() {
  // Have existing geocode info?
  var res = localStorage.getItem("geocode");
  if (res) {
    try {
      onHasGeocode(JSON.parse(res));
    } catch (ex) {
    }
  }

  // URL specifies topic?
  var qs = parse_qs(window.location.hash.substring(1));
  if (qs.topic)
    $('#topic').val(qs.topic);
})

$('#topic-go').click(function() {
  if ($('#address').is(":visible")) {
    // Address entry is still shown - use it.
    submit_address();
  } else {
    // Already geocoded.
    onTopicSubmit();
  }
})

function submit_address() {
  var address = $('#address').val();
  if (!address) {
    alert("Enter your home address so we can find who represents you in Congress.");
    return;
  }
  geocode({
    address: address
  }, true);
}

var geocode_data = null;
function onHasGeocode(geocode) {
  geocode_data = geocode;
  $('#homepage-address').hide()
  $('#homepage-district').fadeIn();
  $('#homepage-district').find('.state').text(geocode.state);
  $('#homepage-district').find('.district').html(geocode.district_html);
  $('#homepage-district').find('.address').text(geocode.address);
  $('#district-link').attr('href',
    'https://www.govtrack.us/congress/members/'
    + geocode.cd.substring(0, 2)
    + "/"
    + parseInt(geocode.cd.substring(2)));
}

$('#topic').click(function() {
  var topic = $('#topic').val();
  if (topic == "")
    history.replaceState(null, null, "#")
  else
    history.replaceState(null, null, "#topic=" + topic)
});

function onTopicSubmit() {
  var topic = $('#topic').val();
  if (topic == "") {
    alert("Select a topic.");
    return;
  }
  if (!geocode_data.cd) { // validate we have the data we need
    alert("Pleae re-enter your address.");
    return;
  }
}