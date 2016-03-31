# -*- coding: utf-8 -*-
from __future__ import print_function

import logging
import json


from . import core
import lambdautils.utils as utils
from .exceptions import KinesisError, FirehoseError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_event(
        kinesis_event, context, output_stream_name, input_delivery_stream_name,
        output_delivery_stream_name, callables):
    """Forwards events to a Kinesis stream (for further processing) and
    to a Kinesis Firehose delivery stream (for persistence in S3 and/or
    Redshift)"""
    events = utils.unpack_kinesis_event(kinesis_event,
                                        deserializer=json.loads)
    logger.info("Going to transform {} events".format(len(events)))
    output_events = core.transform_events(events, callables)
    logger.info(json.dumps(output_events, indent=4))

    if len(output_events):
        if output_stream_name:
            logger.info("Sending {} events to output stream '{}' ...".format(
                len(output_events), output_stream_name))
            resp = utils.send_to_kinesis_stream(output_events,
                                                output_stream_name)
            if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise KinesisError(json.dumps(resp))
            logger.info(resp)

        if input_delivery_stream_name:
            logger.info("Sending {} events to delivery stream '{}' ...".format(
                len(output_events), input_delivery_stream_name))
            resp = utils.send_to_delivery_stream(output_events,
                                                 output_delivery_stream_name)
            if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise FirehoseError(json.dumps(resp))
            logger.info(resp)

    if len(input_delivery_stream_name) > 0:
        logger.info("Sending {} events to delivery stream '{}' ...".format(
            len(events), input_delivery_stream_name))
        resp = utils.send_to_delivery_stream(events,
                                             input_delivery_stream_name)
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise FirehoseError(json.dumps(resp))
        logger.info(resp)

    logger.info("Successfully processed {} Kinesis records:".format(
        len(events)))
