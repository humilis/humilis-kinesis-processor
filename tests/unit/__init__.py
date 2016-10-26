"""Unit test suite utilities."""

import codecs
from copy import deepcopy
import json


def make_kinesis_event(template, records):
    """A sample Kinesis event."""
    encoded_recs = [codecs.encode(json.dumps(rec).encode("utf-8"), "base64")
                    for rec in records]
    records = []
    for rec in encoded_recs:
        this_rec = deepcopy(template)
        this_rec["kinesis"]["data"] = rec
        records.append(this_rec)

    return {"Records": records}
