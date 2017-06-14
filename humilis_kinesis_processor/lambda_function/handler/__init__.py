"""Lambda function entry point."""

# preprocessor:jinja2

import copy
from base64 import b64encode, b64decode
import json
import logging
import os
import zlib

import boto3
import lambdautils.utils as utils
from retrying import retry
import raven
from werkzeug.utils import import_string  # noqa

from .processor import process_event

logger = logging.getLogger()
logger.setLevel(getattr(logging, os.environ.get("LOGGING_LEVEL", "INFO")))


def produce_io_stream_callables():
    """Produces filter/mapper callables for the input and output streams."""
    if utils.in_aws_lambda():
        try:
            globs = dict(import_string=import_string, input=None, output=None)
            exec(
                """
{% set callables = ['batch_mapper', 'mapper', 'filter', 'partition_key'] %}
{% if meta_input %}
input  = {
    {% for k, v in meta_input.items() %}
    {% if k in callables %}
    '{{k}}': '{{v or ''}}' and import_string('{{v}}'),
    {% else %}
    {% if v is mapping %}
    '{{k}}': {
    {% for k1, v1 in v.items() %}
    '{{k1}}': '{{v1}}',
    {% endfor %}
    },
    {% elif v|is_list %}
    '{{k}}': [
    {% for vl in v %}
    {% if vl is mapping %}
    {
    {% for k2, v2 in vl.items() %}
    {% if k2 in callables %}
    '{{k2}}': '{{v2 or ''}}' and import_string('{{v2}}'),
    {% else %}
    '{{k2}}': '{{v2}}',
    {% endif %}
    {% endfor %}
    },
    {% else %}
    '{{vl}}',
    {% endif %}
    {% endfor %}
    ],
    {% else %}
    '{{k}}': '{{v or ''}}',
    {% endif %}
    {% endif %}
    {% endfor %}
}
{% endif %}
{% if meta_output %}
output = [
    {% for o in meta_output %}
    {
        {% for k, v in o.items() %}
        {% if k in callables %}
        '{{k}}': '{{v or ''}}' and import_string('{{v}}'),
        {% else %}
        {% if v is mapping %}
        '{{k}}': {
        {% for k1, v1 in v.items() %}
        '{{k1}}': '{{v1}}',
        {% endfor %}
        },
        {% elif v|is_list %}
        '{{k}}': [
        {% for vl in v %}
        {% if vl is mapping %}
        {
        {% for k2, v2 in vl.items() %}
        {% if k2 in callables %}
        '{{k2}}': '{{v2 or ''}}' and import_string('{{v2}}'),
        {% else %}
        '{{k2}}': '{{v2}}',
        {% endif %}
        {% endfor %}
        },
        {% else %}
        '{{vl}}',
        {% endif %}
        {% endfor %}
        ],
        {% else %}
        '{{k}}': '{{v or ''}}',
        {% endif %}
        {% endif %}
        {% endfor %}
    },
    {% endfor %}
]
{% endif %}
        """, globs)
            return globs["input"], globs["output"]
        except:
            logger.error("Unable to produce I/O callables")
            dsn = utils.get_secret("sentry.dsn",
                                   environment="{{_env.name}}",
                                   stage="{{_env.stage}}")
            if not dsn:
                logger.error("Unable to retrieve Sentry DSN")
            else:
                client = raven.Client(dsn)
                client.captureException()
            # This is a critical error: must re-raise
            raise


def produce_error_stream_callables():
    """Produces filter/mapper callables for error stream."""
    if utils.in_aws_lambda():
        try:
            globs = dict(import_string=import_string, error=None)
            exec(
                """
{% set callables = ['batch_mapper', 'mapper', 'filter', 'partition_key'] %}
{% if meta_error %}
error = {
    {% for k, v in meta_error.items() %}
    {% if k in callables %}
    '{{k}}': '{{v or ''}}' and import_string('{{v}}'),
    {% else %}
    '{{k}}': '{{v}}',
    {% endif %}
    {% endfor %}
}
{% endif %}
            """, globs)
            return globs["error"]
        except:
            logger.error("Unable to produce error callables")
            dsn = utils.get_secret("sentry.dsn",
                                   environment="{{_env.name}}",
                                   stage="{{_env.stage}}")
            if not dsn:
                logger.error("Unable to retrieve Sentry DSN")
            else:
                client = raven.Client(dsn)
                client.captureException()
            # This is a critical error: must re-raise
            raise


@utils.sentry_monitor(
    environment="{{_env.name}}",
    stage="{{_env.stage}}",
    layer="{{_layer.name}}",
    error_stream=produce_error_stream_callables())
def lambda_handler(event, context):
    """Lambda function."""

    if os.environ["ASYNC"].lower() == "true" and not event.get("async"):
        logger.info("Forwarding to async invocation ...")
        resp = invoke_self_async(event, context)
        logger.info(json.dumps(resp, indent=4))
        return
    elif os.environ["ASYNC"].lower() == "true":
        logger.info("Running asynchronously")
        for rec in event["Records"]:
            data = rec["kinesis"]["data"]
            decoded = b64decode(data.encode("utf-8"))
            decompressed = zlib.decompress(decoded).decode()
            rec["kinesis"]["data"] = decompressed

    try:
        input, output = produce_io_stream_callables()
    except Exception as exception:
        # make sentry_monitor re-reraise after notifying sentry
        raise utils.CriticalError(exception)

    return process_event(event, context, input, output)


def invoke_self_async(event, context):
    """
    Have the Lambda invoke itself asynchronously, passing the same event it
    received originally, and tagging the event as 'async' so it's actually
    processed. Code (with modifications) taken from Matthew Preble's blog.
    """

    # Payload limits are very strict in async invocations so use compression
    _compress_records(event)
    event["async"] = True
    called_function = context.invoked_function_arn
    async_batch = os.environ.get("ASYNC_BATCH_SIZE")
    if not async_batch:
        invoke_with_retry(
            FunctionName=called_function,
            InvocationType="Event",
            Payload=json.dumps(event))
    else:
        logger.info("Invoking async with batch_size=%s", async_batch)
        _batch_invoke(called_function, event, int(async_batch))


def _batch_invoke(called_function, event, size):
    """Invoke asynchronously in batches."""
    batch = []
    recs = copy.deepcopy(event["Records"])
    for recix, rec in enumerate(recs):
        batch.append(rec)
        if not (recix + 1) % size:
            event["Records"] = batch
            invoke_with_retry(
                FunctionName=called_function,
                InvocationType="Event",
                Payload=json.dumps(event))
            batch = []

    if batch:
        event["Records"] = batch
        invoke_with_retry(
            FunctionName=called_function,
            InvocationType="Event",
            Payload=json.dumps(event))


def _compress_records(event):
    """Compress the records data."""
    for rec in event["Records"]:
        data = rec["kinesis"]["data"]
        try:
            data = b64encode(zlib.compress(data))
        except TypeError:
            data = b64encode(zlib.compress(data.encode("utf-8"))).decode()
        rec["kinesis"]["data"] = data


@retry(wait_exponential_multiplier=500, wait_exponential_max=5000,
       stop_max_delay=20000)
def invoke_with_retry(**kwargs):
    return boto3.client("lambda").invoke(**kwargs)
