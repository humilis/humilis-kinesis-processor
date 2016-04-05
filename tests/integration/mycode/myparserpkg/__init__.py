"""A sample Python package to test the layer."""

import uuid

from user_agents import parse


def partition_key(event, **kwargs):
    """Produces the partition key for an event."""
    return event.get("client_id", str(uuid.uuid4()))


def parse_ua(event, **kwargs):
    parsed = parse(event["user_agent"])
    event["device_family"] = parsed.device.family or ""
    event["device_brand"] = parsed.device.brand or ""
