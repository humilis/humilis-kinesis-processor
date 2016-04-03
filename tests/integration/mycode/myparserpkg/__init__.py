"""A sample Python package to test the layer."""

from user_agents import parse


def parse_ua(event):
    parsed = parse(event["user_agent"])
    event["device_family"] = parsed.device.family or ""
    event["device_brand"] = parsed.device.brand or ""
