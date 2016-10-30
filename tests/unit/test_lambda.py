"""Test the logic of the Lambda function."""

import copy

from lambdautils.exception import CriticalError, ProcessingError
from mock import Mock
import pytest

from humilis_kinesis_processor.lambda_function.handler.processor import process_event  # noqa
from . import make_kinesis_event
from .. import make_records


def _identity(ev, *args, **kwargs):
    """An identity mapper callable."""
    return ev


def _all(ev, *args, **kwargs):
    """A pass-all filter callable."""
    return True


def _filter_by_index(index):
    """Produce filter callable that filters by index field."""
    def func(ev, *args, **kwargs):
        """Let pass event by the value of the index field."""
        if ev.get("index") == index:
            return True
        else:
            return False
    return func


def _raise_by_index(index):
    """Callable that raises an exception for events with a given index."""

    class DummyException(Exception):

        """A Dummy exception for testing purposes."""

        pass

    def func(ev, *args, **kwargs):
        """Raise an exception if the input event has the given index."""
        if ev.get("index") == index:
            raise DummyException("This is a dummy")
        else:
            return ev

    return func


def _dupper(ev, state_args=None, **kwargs):
    """Mapper that duplicates every input event."""
    return [ev, ev]


def _none(ev, state_args=None, **kwargs):
    """A pass-none filter."""
    return False


def _make_input(filter=None, mapper=None, kstream=None):
    """Make input specs for processor."""
    input = {}
    if filter is not None:
        input["filter"] = Mock(side_effect=filter)
    if mapper is not None:
        input["mapper"] = Mock(side_effect=mapper)
    if kstream is not None:
        input["kinesis_stream"] = kstream

    return input


def _make_output(filter=None, mapper=None, kstream=None, fstream=None):
    """Make outputs specs for processor."""
    o = {}
    if filter is not None:
        o["filter"] = Mock(side_effect=filter)
    if mapper is not None:
        o["mapper"] = Mock(side_effect=mapper)
    if kstream is not None:
        o["kinesis_stream"] = kstream
    if fstream is not None:
        o["firehose_delivery_stream"] = fstream

    return o


@pytest.mark.parametrize(
    "i,os,kputs,fputs,orecs", [
        [_make_input(kstream="k"),
         [
             _make_output(_filter_by_index(0), _dupper, None, "f"),
             _make_output(_filter_by_index(1), None, "k", None)]
         , 1, 1, [2, 1]],
        [_make_input(kstream="k"),
         [
             _make_output(_filter_by_index(0), None, None, "f"),
             _make_output(_filter_by_index(1), None, "k", None)]
         , 1, 1, [1, 1]],
        [[], [], 0, 0, [0]],
        [_make_input(_none, None, "k"),
         [_make_output(_all, _identity, "k", "f")], 0, 0, [0]],
        [_make_input(_all, _identity, "k"),
         [_make_output(_none, _identity, "k", "f")], 0, 0, [0]],
        [_make_input(kstream="k"),
         [_make_output(_all, _dupper, "k", "f")], 1, 1, [4]],
        [_make_input(kstream="k"),
         [_make_output(_all, _identity, "k", "f")], 1, 1, [2]],
        [_make_input(kstream="k"),
            [_make_output(_all, _identity, "k", None)], 1, 0, [2]],
        [_make_input(kstream="k"),
         [_make_output(_all, _identity, None, "k")], 0, 1, [2]],
        [_make_input(kstream="k"),
         [_make_output(_all, _identity, None, None)], 0, 0, [2]],
        [_make_input(kstream="k"),
         [_make_output(_all, _identity, None, None)], 0, 0, [2]]
        ])
def test_process_event(i, os, kputs, fputs, orecs, kinesis_record_template,
                       context, boto3_client):
    """Test processing events."""
    sample_records = make_records(2)
    kinesis_event = make_kinesis_event(kinesis_record_template, sample_records)
    oevents = process_event(kinesis_event, context, i, os)
    assert boto3_client("kinesis").put_records.call_count == kputs
    assert boto3_client("firehose").put_record_batch.call_count == fputs
    assert len(oevents) == len(os)
    for index, evs in enumerate(oevents):
        assert len(evs) == orecs[index]


@pytest.mark.parametrize(
    "i,os,kputs,fputs,frecs", [
        [_make_input(kstream="k"),
         [
             _make_output(_raise_by_index(0), _dupper, None, "f"),
             _make_output(_raise_by_index(1), None, "k", None)],
         1, 1, 2],
        ])
def test_handle_errors(i, os, kputs, fputs, frecs, kinesis_record_template,
                       context, boto3_client, monkeypatch):
    """Test handling processing errors."""
    sample_records = make_records(2)
    kinesis_event = make_kinesis_event(kinesis_record_template, sample_records)

    def raise_processing_error(*args, **kwargs):
        """Raise a ProcessingError exception."""
        raise_processing_error.args = args
        raise_processing_error.kwargs = kwargs
        raise ProcessingError(*args, **kwargs)

    mocked_exception = Mock(side_effect=raise_processing_error)
    monkeypatch.setattr(
        "humilis_kinesis_processor.lambda_function.handler.processor.ProcessingError",  # noqa
        mocked_exception)

    with pytest.raises(ProcessingError):
        process_event(kinesis_event, context, i, os)

    assert len(mocked_exception.side_effect.args[0]) == frecs
    assert boto3_client("kinesis").put_records.call_count == kputs
    assert boto3_client("firehose").put_record_batch.call_count == fputs


def test_bad_mapper_signature(kinesis_record_template, context):
    """Mappers with wrong interfaces should raise CriticalError."""

    def bad_mapper(event, context):
        """A mapper that does not fulfill the mapper interface."""
        return "Hi there!"

    sample_records = make_records(2)
    kinesis_event = make_kinesis_event(kinesis_record_template, sample_records)
    outputp = [{"mapper": Mock(side_effect=bad_mapper)}]
    with pytest.raises(CriticalError):
        process_event(kinesis_event, context, [], outputp)
