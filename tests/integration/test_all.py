# -*- coding: utf-8 -*-
"""Tests the input and output Kinesis streams."""

import json
import time
import uuid


def get_all_records(client, si, limit, timeout=10):
    """Retrieves all records from a Kinesis stream."""
    retrieved_recs = []
    for _ in range(timeout):
        kinesis_recs = client.get_records(ShardIterator=si, Limit=limit)
        si = kinesis_recs["NextShardIterator"]
        retrieved_recs += kinesis_recs["Records"]
        if len(retrieved_recs) == limit:
            # All records have been retrieved
            break
        time.sleep(1)

    return retrieved_recs


def test_error_streams(kinesis, io_stream_names, shard_iterators,
                       bad_payloads):
    """Put and read a record from the input stream."""
    input_stream, _, error_stream = io_stream_names

    # Latest shard iterators after emptying both the input and output streams
    input_si, _, error_si = shard_iterators

    # Put some records in the input stream
    response = kinesis.put_records(
        StreamName=input_stream,
        Records=[
            {
                "Data": payload,
                "PartitionKey": str(uuid.uuid4())
            } for payload in bad_payloads])

    assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    retrieved_recs = get_all_records(kinesis, error_si, len(bad_payloads),
                                     min(max(20, 3*len(bad_payloads)), 150))

    assert len(retrieved_recs) == len(bad_payloads)
    retrieved_events = [json.loads(x["Data"].decode()) for x in retrieved_recs]
    assert not any({"payload", "stage", "layer", "environment"} ^ set(e.keys())
                   for e in retrieved_events)

    retrieved_msgs = set()
    for ev in retrieved_events:
        for p in ev["payload"]:
            retrieved_msgs.add(json.loads(p))

    put_msgs = {json.loads(x) for x in bad_payloads}
    assert not retrieved_msgs.difference(put_msgs)


def test_io_streams_put_get_record(kinesis, io_stream_names, shard_iterators,
                                   payloads):
    """Put and read a record from the input stream."""
    input_stream, output_stream, _ = io_stream_names

    # Latest shard iterators after emptying both the input and output streams
    input_si, output_si, _ = shard_iterators

    # Put some records in the input stream
    response = kinesis.put_records(
        StreamName=input_stream,
        Records=[
            {
                "Data": payload,
                "PartitionKey": str(uuid.uuid4())
            } for payload in payloads])

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    retrieved_recs = get_all_records(kinesis, output_si, len(payloads),
                                     min(max(15, 3 * len(payloads)), 150))

    assert len(retrieved_recs) == len(payloads)
    retrieved_events = [json.loads(x["Data"].decode()) for x in retrieved_recs]
    retrieved_ids = {x["id"] for x in retrieved_events}
    put_ids = {json.loads(x)['id'] for x in payloads}
    assert not retrieved_ids.difference(put_ids)
    assert all(x["browser_version"] == "4.0.4" for x in retrieved_events)
