"""A sample module that contains a mapper function."""

import json

from lambdautils.exception import OutOfOrderError


def input_mapper(event, *args, **kwargs):
    """Throw an OutOfOrderError if the event index is negative."""
    if event["index"] < 0:
        raise OutOfOrderError("Event out of order: {}".format(pretty(event)))

    event["input_mapper"] = True
    return event


def pretty(event):
    """Pretty print an event."""
    return json.dumps(event, indent=4)
