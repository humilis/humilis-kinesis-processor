"""Lambda function entry point."""

# preprocessor:jinja2

import logging

import lambdautils.utils as utils
import raven
from werkzeug.utils import import_string  # noqa

from .processor import process_event

logger = logging.getLogger()


def produce_io_stream_callables():
    """Produces filter/mapper callables for the input and output streams."""
    if utils.in_aws_lambda():
        try:
            globs = dict(import_string=import_string, input=None, output=None)
            exec(
                """
{% set callables = ['mapper', 'filter', 'partition_key'] %}
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
{% set callables = ['mapper', 'filter', 'partition_key'] %}
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

    try:
        input, output = produce_io_stream_callables()
    except Exception as exception:
        # make sentry_monitor re-reraise after notifying sentry
        raise utils.CriticalError(exception)

    return process_event(event, context, input, output)
