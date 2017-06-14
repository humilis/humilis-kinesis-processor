"""Process events in a Kinesis stream."""
from __future__ import print_function

# preprocessor:jinja2

import copy
from collections import namedtuple
import operator
import logging
import os
import json
import sys
import uuid

import lambdautils.utils as utils
from lambdautils.exception import CriticalError, ProcessingError
from werkzeug.utils import import_string  # noqa


logger = logging.getLogger()
logger.setLevel(getattr(logging, os.environ.get("LOGGING_LEVEL", "INFO")))

EventError = namedtuple("EventError", "index event error tb")


class KinesisError(Exception):

    """Kinesis API error."""

    pass


class FirehoseError(Exception):

    """Firehose API Error."""

    pass


def process_event(kevent, context, inputp, outputp):
    """Process records in the incoming Kinesis event."""
    input_events, shard_id = _get_records(kevent)

    # The humilis context to pass to filters and mappers
    hcontext = _make_humilis_context(shard_id=shard_id, lambda_context=context)

    nbevents = len(input_events)
    logger.info("Going to process %s events", nbevents)
    logger.info("First event: %s", pretty(input_events[0]))

    # Records that threw an exception in the input or output pipelines
    failed = []
    if inputp:
        input_delivery_stream = inputp.get("firehose_delivery_stream")
        if input_delivery_stream:
            for stream in input_delivery_stream:
                send_to_delivery_stream(input_events, stream)

        # The input pipeline is enforced to be 1-to-1
        events, ifailed = run_pipeline(
            inputp, copy.deepcopy(input_events), hcontext, "input")
        if ifailed:
            logger.error(
                "%s events failed to be processed: %s", len(ifailed), ifailed)
        failed += ifailed
    else:
        events = input_events

    if events and outputp:
        # The original indices of the events
        indices = [i for i in range(nbevents)
                   if i not in {f.index for f in failed}]
        oevents, ofailed = produce_outputs(outputp, events, hcontext)
        # Remap the indices of the errors
        ofailed = [EventError(indices[err.index],
                              input_events[indices[err.index]],
                              err.error,
                              err.tb)
                   for err in ofailed]
        if ofailed:
            logger.error(
                "%s events failed to be processed: %s", len(ofailed), ofailed)
        failed += ofailed
        # To make the processing task as atomic as possible we deliver the
        # events to the output streams only after all outputs are produced.
        deliver_outputs(outputp, oevents)
    else:
        if outputp:
            oevents = [[] for _ in outputp]
        else:
            oevents = []

    if failed:
        raise ProcessingError(sorted(failed, key=operator.attrgetter("index")))

    return oevents


def _make_humilis_context(**kwargs):
    """Produce the humilis context dict to pass to filters and mappers."""
    return dict(
        environment=os.environ.get("HUMILIS_ENVIRONMENT"),
        layer=os.environ.get("HUMILIS_LAYER"),
        stage=os.environ.get("HUMILIS_STAGE"),
        **kwargs)


def _get_records(kevent):
    """Unpack records from a Kinesis event."""
    events, shard_id = utils.unpack_kinesis_event(
        kevent,
        deserializer="{{kinesis_deserializer}}" \
                and "{{kinesis_desearializer}}" != "None" \
                and import_string("{{kinesis_deserializer}}"),
        unpacker="{{kinesis_unpacker}}" \
                and "{{kinesis_unpacker}}" != "None" \
                and import_string("{{kinesis_unpacker}}"),
        embed_timestamp="{{received_at_field}}"
        )

    return events, shard_id


def deliver_outputs(output, oevents):
    """Deliver the output events to their corresponding streams."""
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
            for stream in delivery_stream:
                send_to_delivery_stream(oevents[i], stream)
        else:
            logger.info("No FH delivery stream: not forwarding to FH")


def produce_outputs(outputs, events, context):
    """Produces the output event streams."""
    oevents = []
    failed = {}
    for oindex, output in enumerate(outputs):
        logger.info("Producing output #%s", oindex)
        # An event must succeed in all outputs to be considered successful
        processed, this_failed = run_pipeline(
            output, copy.deepcopy(events), context, "output {}".format(oindex))
        if this_failed:
            logger.info("%s events failed for this output", len(this_failed))
            logger.info("First failed event: %s", pretty(this_failed[0].event))
        for err in this_failed:
            # Record only the first exception raised by an event
            if err.index not in failed:
                failed[err.index] = err
        oevents.append(processed)

    return oevents, [err for idx, err in sorted(failed.items())]


def run_pipeline(pipeline, events, context, name="unnamed"):
    """Apply a filter and a mapper to a list of events."""

    logger.info("Processing %s events with pipeline '%s'.", len(events), name)

    batch_mapper = pipeline.get("batch_mapper")
    if batch_mapper:
        events = batch_mapper(copy.deepcopy(events), context)

    pfilter = pipeline.get("filter")
    pmapper = pipeline.get("mapper")
    failed = []
    processed = []
    for index, event in enumerate(events):
        try:
            if pfilter and not pfilter(copy.deepcopy(event), context):
                # Skip this event in this pipeline
                continue
            if pmapper:
                mapped = pmapper(copy.deepcopy(event), context)
                if mapped is None:
                    continue
                if isinstance(mapped, dict):
                    # backwards compatibility
                    mapped = [mapped]
                if not isinstance(mapped, list):
                    raise CriticalError("Mapper must return a list of dicts.")
                if name == "input" and len(mapped) != 1:
                    raise CriticalError("Input mappers must be 1-to-1")
                processed += mapped
            else:
                processed.append(event)
        except CriticalError:
            raise
        except Exception as err:
            # Add an annotation to support error expiration
            event = utils.annotate_error(event, err)
            failed.append(EventError(index, event, err, sys.exc_info()))

    return processed, failed


def send_to_delivery_stream(events, delivery_stream):
    """Send events to a Firehose delivery stream."""
    if events:
        logger.info("Sending %d events to delivery stream '%s' ...",
                    len(events), delivery_stream)
        stream_name = delivery_stream["stream_name"]
        if "filter" in delivery_stream:
            logger.info("Applying filter before delivery")
            events = [copy.deepcopy(ev) for ev in events
                      if delivery_stream["filter"](ev)]
            logger.info("Selected %d events for delivery", len(events))

        if not events:
            logger.info("All events were filtered out: nothing delivered")
            return

        if "mapper" in delivery_stream:
            logger.info("Mapping %d events before delivery", len(events))
            events = [delivery_stream["mapper"](copy.deepcopy(ev))
                      for ev in events]

        logger.info("First delivered event: %s", pretty(events[0]))
        resp = utils.send_to_delivery_stream(events, stream_name)
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise FirehoseError(json.dumps(resp))
        logger.info(resp)


def send_to_kinesis_stream(events, stream, partition_key):
    """Send events to an ouput Kinesis stream."""
    if events:
        logger.info("Sending %d events to '%s' ...", len(events), stream)
        logger.info("First sent event: %s", pretty(events[0]))
        resp = utils.send_to_kinesis_stream(
            events,
            stream,
            partition_key=partition_key,
            packer="{{kinesis_packer}}" \
                    and "{{kinesis_packer}}" != "None" \
                    and import_string("{{kinesis_packer}}"),
            serializer="{{kinesis_serializer}}" \
                    and "{{kinesis_serializer}}" != "None" \
                    and import_string("{{kinesis_serializer}}"))
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise KinesisError(json.dumps(resp))
        logger.info(resp)


def pretty(event):
    """Pretty print an event."""
    return json.dumps(event, indent=4)
