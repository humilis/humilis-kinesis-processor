"""Test the logic of the Lambda function."""

import copy

from mock import Mock

import pytest

from humilis_kinesis_processor.lambda_function.handler.processor import process_event  # noqa
from lambdautils.exception import CriticalError


def _identity(ev, state_args=None, **kwargs):
    """An identity mapper callable."""
    return ev


def _all(ev, state_args=None, **kwargs):
    """A pass-all filter callable."""
    return True


def _dupper(ev, state_args=None, **kwargs):
    """Duplicates every input event."""
    return [ev, ev]


def _none(ev, state_args=None, **kwargs):
    """A pass-none filter callable."""
    return False


def _make_input(filter=None, mapper=None, kstream=None):
    input = {}
    if filter is not None:
        input["filter"] = Mock(side_effect=filter)
    if mapper is not None:
        input["mapper"] = Mock(side_effect=mapper)
    if kstream is not None:
        input["kinesis_stream"] = kstream

    return input


def _make_output(filter=None, mapper=None, kstream=None, fstream=None, n=1):
    o = {}
    if filter is not None:
        o["filter"] = Mock(side_effect=filter)
    if mapper is not None:
        o["mapper"] = Mock(side_effect=mapper)
    if kstream is not None:
        o["kinesis_stream"] = kstream
    if fstream is not None:
        o["firehose_delivery_stream"] = fstream

    return [copy.deepcopy(o) for _ in range(n)]


@pytest.mark.parametrize(
    "e,l,s,i,os,kputs,fputs", [
        ["e", "l", "s",
         _make_input(kstream="k"),
         _make_output(_all, _dupper, "k", "f", 2), 2, 2],
        ["e", "l", "s",
         _make_input(kstream="k"),
         _make_output(_all, _identity, "k", "f", 2), 2, 2],
        ["e", "l", "s",
         _make_input(kstream="k"),
         _make_output(_all, _identity, "k", None, 2), 2, 0],
        ["e", "l", "s",
         _make_input(kstream="k"),
         _make_output(_all, _identity, None, "k", 2), 0, 2],
        ["e", "l", "s",
         _make_input(kstream="k"),
         _make_output(_all, _identity, None, None, 2), 0, 0],
        ["e", "l", "s",
         _make_input(_none, None, "k"),
         _make_output(_all, _identity, "k", "f"), 0, 0],
        ["e", "l", "s",
         _make_input(_all, _identity, "k"),
         _make_output(_none, _identity, "k", "f", 2), 0, 0],
        ["e", "l", "s", [], [], 0, 0]
        ])
def test_process_event(e, l, s, i, os, kputs, fputs, kinesis_event, events,
                       context, boto3_client, monkeypatch):
    """Process events."""
    process_event(kinesis_event, context, "e", "l", "s", i, os)

    assert boto3_client("kinesis").put_records.call_count == kputs
    assert boto3_client("firehose").put_record_batch.call_count == fputs

    if i:
        ifilter = i.get("filter")
    else:
        ifilter = None

    if ifilter:
        assert ifilter.call_count == len(events)
        # Need to reset the call count because events is a parametrized fixture
        ifilter.reset_mock()

    if i:
        imapper = i.get("mapper")
    else:
        imapper = None

    if imapper:
        if ifilter is None or ifilter.side_effect == _all:
            assert imapper.call_count == len(events)
        elif ifilter.side_effect == _none:
            assert imapper.call_count == 0

        imapper.reset_mock()

    for o in os:
        ofilter = o.get("filter")
        if ofilter:
            if ifilter is None or ifilter == _all:
                assert ofilter.call_count == len(events)
            ofilter.reset_mock()

        omapper = o.get("mapper")
        pk = o.get("partition_key")
        if (ifilter is None or ifilter.side_effect == _all) and \
                (ofilter is None or ofilter.side_effect == _all):
            if omapper:
                assert omapper.call_count == len(events)
            if pk:
                assert pk.call_count == len(events)
        else:
            if omapper:
                assert omapper.call_count == 0
            if pk:
                assert pk.call_count == 0

        if omapper:
            omapper.reset_mock()

        if pk:
            pk.reset_mock()


def test_bad_callable(kinesis_event, context):
    """Bad mappers should raise an exception."""

    def bad_mapper(ev, context):
        return "I should never return a string!"

    os = [{"mapper": Mock(side_effect=bad_mapper)}]
    with pytest.raises(CriticalError):
        process_event(kinesis_event, context, "e", "l", "s", [], os)
