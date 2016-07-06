from __future__ import print_function

import copy
import logging
import json

import lambdautils.utils as utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class KinesisError(Exception):
    pass


class FirehoseError(Exception):
    pass


def process_event(
        kinesis_event, context, environment, layer, stage, input, output):
    """Forwards events to a Kinesis stream (for further processing) and
    to a Kinesis Firehose delivery stream (for persistence in S3 and/or
    Redshift)"""

    events, shard_id = utils.unpack_kinesis_event(
        kinesis_event, deserializer=json.loads,
        embed_timestamp="receivedAt")

    input_delivery_stream = input.get("firehose_delivery_stream")
    if input_delivery_stream:
        send_to_delivery_stream(events, input_delivery_stream)

    # The humilis context to pass to filters and mappers
    humilis_context = dict(environment=environment, layer=layer, stage=stage,
                           shard_id=shard_id, lambda_context=context)

    logger.info("Going to process {} events".format(len(events)))
    logger.info("First event: {}".format(pretty(events[0])))

    events = process_input(input, events, humilis_context)
    if not events:
        return

    oevents = produce_outputs(output, events, humilis_context)

    # To make the processing task as atomic as possible we deliver the events
    # to the output streams only after all outputs have been produced.
    deliver_outputs(output, oevents)


def deliver_outputs(output, oevents):
    """Delivers the output events to their corresponding streams."""
    for i, o in enumerate(output):
        logger.info("Forwarding output #{}".format(i))
        stream = o.get("kinesis_stream")

        if not oevents[i]:
            logger.info("All events have been filtered out for this output")
            continue

        if stream:
            send_to_kinesis_stream(oevents[i], stream, o.get("partition_key"))
        else:
            logger.info("No output Kinesis stream: not forwarding to Kinesis")

        delivery_stream = o.get("firehose_delivery_stream")
        if delivery_stream:
            send_to_delivery_stream(oevents[i], delivery_stream)
        else:
            logger.info("No FH delivery stream: not forwarding to FH")


def produce_outputs(output, events, context):
    """Produces the output event streams."""
    oevents = []
    _all = lambda ev, context: True
    for i, o in enumerate(output):
        logger.info("Producing output #{}".format(i))
        ofilter = o.get("filter", _all)
        if not ofilter:
            ofilter = _all
        oevents.append([copy.deepcopy(ev) for ev in events
                        if ofilter(ev, context)])
        logger.info("Selected {} events".format(len(oevents[i])))

        if not oevents[i]:
            continue

        omapper = o.get("mapper")
        if omapper:
            mapped_evs = []
            for ev in oevents[i]:
                mapped_evs.append(omapper(ev, context))
            oevents[i] = mapped_evs
            logger.info("Mapped {} events".format(len(oevents[i])))
        else:
            logger.info("No output mapper: doing nothing")

        logger.info("First output event: {}".format(pretty(mapped_evs[0])))

    return oevents


def process_input(input, events, context):
    """Filters and maps the input events."""
    if input.get("filter"):
        logger.info("Filtering input events")
        events = [ev for ev in events if input["filter"](ev, context)]
        if not events:
            logger.info("All input events were filtered out: nothing to do")
            return []
        else:
            logger.info("Selected {} input events".format(len(events)))
    else:
        logger.info("No input filter: using all input events")

    if input.get("mapper"):
        logger.info("Mapping input evets")
        mapped_evs = []
        for ev in events:
            mapped_evs.append(input["mapper"](ev, context))

        logger.info("First mapped input events: {}".format(
            pretty(mapped_evs[0])))
    else:
        mapped_evs = events
        logger.info("No input mapping: processing raw input events")

    return mapped_evs


def send_to_delivery_stream(events, delivery_stream):
    if events:
        logger.info("Sending events to delivery stream '{}' ...".format(
            len(events), delivery_stream))
        resp = utils.send_to_delivery_stream(events, delivery_stream)
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise FirehoseError(json.dumps(resp))
        logger.info(resp)


def send_to_kinesis_stream(events, stream, partition_key):
    if events:
        logger.info("Sending {} events to stream '{}' ...".format(
            len(events), stream))

        logger.info("Using partition key: {}".format(partition_key))
        resp = utils.send_to_kinesis_stream(events, stream,
                                            partition_key=partition_key)
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise KinesisError(json.dumps(resp))
        logger.info(resp)


def pretty(event):
    return json.dumps(event, indent=4)
