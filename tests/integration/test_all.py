"""Run integration tests."""

import json
import uuid


from . import get_all_records, get_shard_iterators
from .. import make_records


def test_out_of_order_error(
    kinesis, input_stream_name, output_stream_name, error_stream_name):
    """Test handling a ProcessingError exception in a mapper."""

    sample_records = make_records(2)
    # This will cause the input mapper to raise an OutOfOrderError
    sample_records[0]["index"] = -100
    _assert_non_critical_error(kinesis, sample_records, input_stream_name,
                               output_stream_name, error_stream_name)


def test_processing_error(
    kinesis, input_stream_name, output_stream_name, error_stream_name):
    """Test handling a ProcessingError exception in a mapper."""

    sample_records = make_records(2)
    # This will cause the input filter to raise a KeyError
    del sample_records[0]["id"]
    _assert_non_critical_error(kinesis, sample_records, input_stream_name,
                               output_stream_name, error_stream_name)


def _assert_non_critical_error(kinesis, recs, istream, ostream, estream):
    """Asserts that a non-critical error is routed to the error stream."""
    # Get the shard iterators *before* you put records at the input
    shard_iterators = get_shard_iterators(kinesis, ostream)
    error_shard_iterators = get_shard_iterators(kinesis, estream)
    _put_records(kinesis, istream, recs)
    nbrecs = len(recs)
    retrieved_recs = _retrieve_records(2*(nbrecs-1), kinesis, shard_iterators)
    assert len(retrieved_recs) == 2*(nbrecs-1)
    retrieved_error_recs = _retrieve_records(1, kinesis, error_shard_iterators)
    assert len(retrieved_error_recs) == 1


def test_io_streams_put_get_record(
        kinesis, input_stream_name, output_stream_name):
    """Put records at the input, then read them from the output."""

    sample_records = make_records(2)
    # Get the shard iterators *before* you put records at the input
    shard_iterators = get_shard_iterators(kinesis, output_stream_name)
    _put_records(kinesis, input_stream_name, sample_records)

    nbrecs = len(sample_records)
    retrieved_recs = _retrieve_records(2*nbrecs, kinesis, shard_iterators)

    # Two pipelines that produce one event for each input event
    assert len(retrieved_recs) == 2*nbrecs
    retrieved_recs = [json.loads(x["Data"].decode()) for x in retrieved_recs]
    retrieved_ids = {x["id"] for x in retrieved_recs}
    put_ids = {x['id'] for x in sample_records}
    assert not retrieved_ids.difference(put_ids)
    assert all("input_filter" not in ev and "input_mapper" in ev and
               "received_at" in ev for ev in retrieved_recs)
    assert all("batch_mapped" in ev for ev in retrieved_recs)

def test_set_get_state(
        kinesis, input_stream_name, output_stream_name):
    """Put and read a record from the input stream."""

    sample_records = make_records(2)
    nbrecs = len(sample_records)
    # Get the shard iterators *before* you put the records at the input
    shard_iterators = get_shard_iterators(kinesis, output_stream_name)
    # Put the same record multiple times in the stream
    _put_records(kinesis, input_stream_name,
                 [sample_records[0] for _ in range(nbrecs)])

    retrieved_recs = _retrieve_records(nbrecs, kinesis, shard_iterators)

    # The same input event should be sent to the two output streams
    assert len(retrieved_recs) == 2
    retrieved_event = json.loads(retrieved_recs[0]["Data"].decode())
    retrieved_id = retrieved_event["id"]
    put_id = sample_records[0]["id"]
    assert put_id == retrieved_id
    assert "input_filter" not in retrieved_event \
        and "input_mapper" in retrieved_event \
        and "received_at" in retrieved_event


def _put_records(kinesis, input_stream_name, records):
    """Put records in the input Kinesis stream."""
    response = kinesis.put_records(
        StreamName=input_stream_name,
        Records=[
            {
                "Data": json.dumps(rec),
                "PartitionKey": str(uuid.uuid4())
            } for rec in records])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def _retrieve_records(nbrecs, kinesis, shard_iterators):
    """Retrieve records from the output Kinesis stream."""
    retrieved_recs = []
    # Just some rule-of-thumb timeout
    timeout = min(max(20, 5 * nbrecs), 120)
    for shard_iterator in shard_iterators:
        retrieved_recs += get_all_records(
            kinesis, shard_iterator, nbrecs, timeout)

    return retrieved_recs
