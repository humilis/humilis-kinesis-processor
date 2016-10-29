"""Global test utilities."""

import uuid


def make_records(nbrecs):
    """A batch of records to be ingested by Kinesis."""
    return [{
        "id": str(uuid.uuid4()).replace("-", ""),
        "index": index,
        "timestamp": "2016-01-22T01:45:44.235+01:00",
        "client_id": "1628457772.1449082074",
        "user_agent": ("Mozilla/5.0 (Linux; U; Android 4.0.4; en-gb; "
                       "GT-I9300 Build/IMM76D) AppleWebKit/534.30 (KHTML, "
                       "like Gecko) Version/4.0 Mobile Safari/534.30"),
        "url": "http://staging.findhotel.net/?lang=nl-NL",
        "referrer_url": "http://staging.findhotel.net/"
    } for index in range(nbrecs)]
