"""Process events in a Kinesis stream."""
from __future__ import print_function

import copy
from collections import namedtuple
import operator
import logging
import os
import json

import lambdautils.utils as utils
from lambdautils.exception import CriticalError, ProcessingError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EventError = namedtuple("EventError", "index event error")


class KinesisError(Exception):

    """Kinesis API error."""

    pass


class FirehoseError(Exception):

    """Firehose API Error."""

    pass


def process_event(kevent, context, inputp, outputp):
    """Process records in the incoming Kinesis event."""

    events, shard_id = _get_records(kevent)

    # The humilis context to pass to filters and mappers
    hcontext = _make_humilis_context(shard_id=shard_id, lambda_context=context)

    logger.info("Going to process %s events", len(events))
    logger.info("First event: %s", pretty(events[0]))

    # Records that threw an exception in the input or output pipelines
    failed = []
    if inputp:
        input_delivery_stream = inputp.get("firehose_delivery_stream")
        if input_delivery_stream:
            for stream in input_delivery_stream:
                send_to_delivery_stream(events, stream)

        events, ifailed, _ = run_pipeline(inputp, events, hcontext, "input")
        failed += ifailed

    if events and outputp:
        oevents, ofailed = produce_outputs(outputp, events, hcontext)
        failed += ofailed
        # To make the processing task as atomic as possible we deliver the
        # events to the output streams only after all outputs are produced.
        deliver_outputs(outputp, oevents)

    if failed:
        raise ProcessingError(sorted(failed, key=operator.attrgetter("index")))


def _make_humilis_context(**kwargs):
    """Produce the humilis context dict to pass to filters and mappers."""
    return dict(
        environment=os.environ.get("HUMILIS_ENVIRONMENT"),
        layer=os.environ.get("HUMILIS_LAYER"),
        stage=os.environ.get("HUMILIS_STAGE"),
        **kwargs)


def _get_records(kevent):
    """Unpack records from a Kinesis event."""
    try:
        events, shard_id = utils.unpack_kinesis_event(
            kevent, deserializer=json.loads,
            embed_timestamp="received_at")
    except:
        events = kevent
        shard_id = 1

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
    failed = []
    for oindex, output in enumerate(outputs):
        logger.info("Producing output #%s", oindex)
        # An event must succeed in all outputs to be considered successful
        processed, this_failed, events = run_pipeline(
            output, [copy.deepcopy(ev) for ev in events], context, "output")
        failed += this_failed
        oevents.append(processed)

    return oevents, failed


def run_pipeline(pipeline, events, context, name="unnamed"):
    """Apply a filter and a mapper to a list of events."""

    failed = []
    succeeded = events
    ifilter = pipeline.get("filter")
    imapper = pipeline.get("mapper")

    logger.info("Processing '%s' pipeline.", name)

    if ifilter:
        logger.info("Filtering %s events.", len(events))
        events, ffailed, succeeded = _filter_events(ifilter, events, context)
        failed += ffailed
    else:
        logger.info("No filter: selecting all events")
        ffailed = []
        succeeded = events

    if imapper:
        logger.info("Mapping %s events.", len(events))
        mapped, mfailed, succeeded = _map_events(imapper, events, context)
        failed = sorted(ffailed + mfailed, key=operator.attrgetter("index"))
    else:
        mapped = events
        succeeded = events
        logger.info("No mapper")

    return mapped, failed, succeeded


def _filter_events(filterf, events, context):
    """Safely apply filter to a set of events and report failed events."""
    failed = []
    succeeded = []
    selected = []
    for index, event in enumerate(events):
        try:
            if filterf(event, context):
                selected.append(event)
            succeeded.append(event)
        except CriticalError:
            raise
        except Exception as err:
            failed.append(EventError(index, event, err))

    if failed:
        logger.info("Failed to filter %s events.", len(failed))

    if selected:
        logger.info("Selected %s events.", len(selected))
    else:
        logger.info("Filtered out all events: nothing to do.")

    return selected, failed, succeeded


def _map_events(mapf, events, context):
    """Safely apply mapper to selected events."""
    failed = []
    succeeded = []
    mapped = []
    for index, event in enumerate(events):
        try:
            mapped_events = mapf(event, context)
            if isinstance(mapped_events, dict):
                # 1-to-1 mapping: for backwards compatibility
                mapped.append(mapped_events)
            elif isinstance(mapped_events, list):
                # 1-to-many mapping
                mapped += mapped_events
            else:
                raise CriticalError("Mapper must return a list of dicts")
            succeeded.append(event)
        except CriticalError:
            raise
        except Exception as err:
            failed.append(EventError(index, event, err))

    if failed:
        logger.info("Failed to map %s/%s events.", len(failed), len(events))

    if mapped:
        logger.info("Mapper produced %s events for %s incoming events.",
                    len(mapped), len(events))
        logger.info("First mapped event: %s", pretty(mapped[0]))

    return mapped, failed, succeeded


def send_to_delivery_stream(events, delivery_stream):
    """Send events to a Firehose delivery stream."""
    if events:
        logger.info("Sending %s events to delivery stream '%s' ...",
                    len(events), delivery_stream)
        resp = utils.send_to_delivery_stream(events, delivery_stream)
        if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise FirehoseError(json.dumps(resp))
        logger.info(resp)


def send_to_kinesis_stream(events, stream, partition_key):
    """Send events to an ouput Kinesis stream."""
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
    """Pretty print an event."""
    return json.dumps(event, indent=4)
