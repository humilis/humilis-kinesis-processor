"""A dummy module for testing purposes."""

import logging
import os
import uuid

import lambdautils.state as state

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def partition_key(event):
    return event.get("client_id", str(uuid.uuid4()))


def input_filter(event, *args, **kwargs):
    if os.environ.get("mydummyvar") != "mydummyval":
        raise ValueError("Unable to retrieve 'mydummyvar' from environment")
    event["input_filter"] = True
    val = state.get_state(event["id"])
    if val:
        logger.info("Retrieved state key '{}': '{}'".format(event["id"], val))
        return False
    else:
        logger.info("State key '{}' not found".format(event["id"]))
        state.set_state(event["id"], "hello there")

    return True


def output_filter_1(event, *args, **kwargs):
    event["output_filter_1"] = True
    return True


def output_mapper_1(event, *args, **kwargs):
    event["output_mapper_1"] = True
    return event


def output_mapper_2(event, *args, **kwargs):
    event["output_mapper_2"] = True
    return event


def output_mapper_2b(event, *args, **kwargs):
    event["output_mapper_2b"] = True
    return event


def output_filter_2b(event, *args, **kwargs):
    return True
