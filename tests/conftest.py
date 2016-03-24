"""Unit test configuration."""
from __future__ import unicode_literals

import pytest
import json
import uuid


@pytest.fixture(scope="session", params=[1, 5])
def events(request):
    """A batch of events to be ingested by Kinesis."""
    return [{
        "id": str(uuid.uuid4()).replace("-", ""),
        "timestamp": "2016-01-22T01:45:44.235+01:00",
        "client_id": "1628457772.1449082074",
        "user_agent": ("Mozilla/5.0 (Linux; U; Android 4.0.4; en-gb; "
                       "GT-I9300 Build/IMM76D) AppleWebKit/534.30 (KHTML, "
                       "like Gecko) Version/4.0 Mobile Safari/534.30"),
        "url": "http://staging.findhotel.net/?lang=nl-NL",
        "referrer_url": "http://staging.findhotel.net/"
    } for _ in range(request.param)]


@pytest.fixture(scope="session", params=[1, 10])
def bad_events(request):
    """A batch of bad events to be sent to Kinesis."""
    # Having a missing timestamp is a critical error: these events should be
    # sent to the error stream
    return ["I am bad!" for _ in range(request.param)]


@pytest.fixture(scope="session")
def payloads(events):
    """A base 64 encoded data record."""
    payloads = []
    for kr in events:
        record = json.dumps(kr)
        payload = record
        payloads.append(payload)
    return payloads


@pytest.fixture(scope="session")
def bad_payloads(bad_events):
    """A base 64 encoded data record."""
    payloads = []
    for kr in bad_events:
        record = json.dumps(kr)
        payload = record
        payloads.append(payload)
    return payloads
