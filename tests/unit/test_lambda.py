"""Test the logic of the Lambda function."""
from mock import Mock

import pytest

from humilis_kinesis_processor.lambda_function.handler.processor import process_event  # noqa


def _identity(ev, state_args=None, **kwargs):
    """An identity mapper callable."""
    return ev


def _all(ev, state_args=None, **kwargs):
    """A pass-all filter callable."""
    return True


def _none(ev, state_args=None, **kwargs):
    """A pass-none filter callable."""
    return False


_input = {
    "kinesis_stream": "iks",
    "firehose_delivery_stream": "ifhs",
    "mapper": Mock(side_effect=_identity),
    "filter": Mock(side_effect=_all)}


_output = [{
    "kinesis_stream": "oks1",
    "firehose_delivery_stream": "ofhs1",
    "mapper": Mock(side_effect=_identity),
    "filter": Mock(side_effect=_all),
    "partition_key": Mock(size_effect=lambda ev: ev.get("client_id"))
    },
    {
    "kinesis_stream": "oks2",
    "firehose_delivery_stream": "ofhs2",
    "mapper": Mock(side_effect=_identity),
    "filter": Mock(side_effect=_all)
    }]


@pytest.mark.parametrize(
    "e,l,s,i,os,kputs,fputs", [
        ["e", "l", "s",
            {
                "kinesis_stream": "iks",
            },
            [
                {
                    "kinesis_stream": "oks1",
                    "firehose_delivery_stream": "ofhs1",
                    "mapper": Mock(side_effect=_identity),
                    "filter": Mock(side_effect=_all)},
                {
                    "kinesis_stream": "oks2",
                    "firehose_delivery_stream": "ofhs2",
                    "mapper": Mock(side_effect=_identity),
                    "filter": Mock(side_effect=_none)}
                ],
            1, 1],
        ["e", "l", "s", _input, _output, 2, 3],
        ["e", "l", "s",
            {
                "kinesis_stream": "iks",
            },
            [{
                "kinesis_stream": "oks1",
                "firehose_delivery_stream": "ofhs1",
                "mapper": Mock(side_effect=_identity),
                "filter": Mock(side_effect=_all)}],
            1, 1],
        ["e", "l", "s",
            {
                "kinesis_stream": "iks",
                "filter": Mock(side_effect=_none)
            },
            [{
                "kinesis_stream": "oks1",
                "firehose_delivery_stream": "ofhs1",
                "mapper": Mock(side_effect=_identity),
                "filter": Mock(side_effect=_all)}],
            0, 0],
        ["e", "l", "s", _input, [], 0, 1],
        ["e", "l", "s",
            {
                "kinesis_stream": "iks",
            },
            [], 0, 0]
        ])
def test_process_event(e, l, s, i, os, kputs, fputs, kinesis_event, events,
                       context, boto3_client, monkeypatch):
    """Process events."""
    process_event(kinesis_event, context, "e", "l", "s", i, os)

    assert boto3_client("kinesis").put_records.call_count == kputs
    assert boto3_client("firehose").put_record_batch.call_count == fputs

    ifilter = i.get("filter")
    if ifilter:
        assert ifilter.call_count == len(events)
        # Need to reset the call count because events is a parametrized fixture
        ifilter.reset_mock()
    imapper = i.get("mapper")
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
