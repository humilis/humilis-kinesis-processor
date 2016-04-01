# -*- coding: utf-8 -*-
"""Tests the input and output Kinesis streams."""

import json
import time
import uuid


def get_all_records(client, si, limit, timeout=10):
    """Retrieve all records from a Kinesis stream."""
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


def test_io_streams_put_get_record(kinesis, io_stream_names, shard_iterators,
                                   payloads, events):
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
    assert all("device_family" in ev for ev in retrieved_events)
