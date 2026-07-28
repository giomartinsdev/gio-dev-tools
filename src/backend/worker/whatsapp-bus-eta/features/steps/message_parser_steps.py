from behave import given, then, use_step_matcher, when

from src.domain.message_parser import parse_evolution_payload

use_step_matcher("re")


@given(r'an Evolution payload with jid "([^"]+)" and text "([^"]*)"\Z')
def step_payload_text(context, jid, text):
    context.payload = {
        "data": {"key": {"remoteJid": jid, "fromMe": False}, "message": {"conversation": text}},
    }


@given(r'an Evolution payload with jid "([^"]+)" and text "([^"]*)" from me')
def step_payload_text_from_me(context, jid, text):
    context.payload = {
        "data": {"key": {"remoteJid": jid, "fromMe": True}, "message": {"conversation": text}},
    }


@given(r'an Evolution payload with jid "([^"]+)" and location (-?[\d.]+) (-?[\d.]+)')
def step_payload_location(context, jid, lat, lon):
    context.payload = {
        "data": {
            "key": {"remoteJid": jid, "fromMe": False},
            "message": {"locationMessage": {"degreesLatitude": float(lat), "degreesLongitude": float(lon)}},
        },
    }


@when("I parse the Evolution payload")
def step_parse(context):
    context.parsed = parse_evolution_payload(context.payload)


@then(r'the parsed remote jid is "([^"]+)"')
def step_jid(context, jid):
    assert context.parsed.remote_jid == jid


@then(r'the parsed text is "([^"]*)"')
def step_text(context, text):
    assert context.parsed.text == text


@then("no location was parsed")
def step_no_location(context):
    assert context.parsed.lat is None and context.parsed.lon is None


@then(r"the parsed latitude is (-?[\d.]+) and longitude is (-?[\d.]+)")
def step_lat_lon(context, lat, lon):
    assert context.parsed.lat == float(lat)
    assert context.parsed.lon == float(lon)


@then("the parsed message is from me")
def step_from_me(context):
    assert context.parsed.from_me is True
