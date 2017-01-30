// Put footer at the bottom.
$('#body').css({
  minHeight: $(window).height() - $('header').outerHeight() - $('footer').outerHeight() - 1
});

$('#use-my-address').click(function() {
  if (!("geolocation" in navigator)) {
    alert("Location is not available.");
    return;
  }
  ga('send', 'event', 'Interactions', 'location', 'geolocation');
  modal_operation(function(operation_finished) {
    navigator.geolocation.getCurrentPosition(function(position) {
      geocode({
        longitude: position.coords.longitude,
        latitude: position.coords.latitude
        });
      operation_finished(); // do this after we start the geocode ajax call so that the modal stays up
    }, function(err) {
      operation_finished();
      alert("Your location is not available.");
    }, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 15000
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

function reset_address() {
  $('#homepage-district').hide();
  $('#homepage-address').show();
  reset_topic();
}

$(function() {
  // Have existing geocode info?
  var res = localStorage.getItem("geocode");
  if (res) {
    try {
      ga('send', 'event', 'Interactions', 'location', 'returning-user');
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
  ga('send', 'event', 'Interactions', 'location', 'address');
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

$('#topic').change(function() {
  // Update URL.
  var topic = $('#topic').val();
  if (topic == "")
    history.replaceState(null, null, "#")
  else
    history.replaceState(null, null, "#topic=" + topic)

  // If a topic was already shown, update it.
  if (topic && $('#homepage-action').is(":visible"))
    onTopicSubmit();
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

  ga('send', 'event', 'Interactions', 'get-instructions', 'topic:'+topic);

  ajax_with_indicator({
    method: "POST",
    url: "/_action",
    data: {
      campaign: topic,
      cd: geocode_data.cd
    },
    success: function(res) {
      //console.log(res);
      $('#topic-go').hide();
      $('#homepage-action').fadeIn();
      $('#homepage-action>div').html(res.html);
    }
  })  
}

function reset_topic() {
   $('#homepage-action').hide();
   $('#topic-go').show();
}
