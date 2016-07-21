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


def test_io_streams_put_get_record(
        environment, kinesis, payloads, shard_iterators, events,
        input_stream_name, output_stream_name):
    """Put and read a record from the input stream."""

    # Put some records in the input stream
    response = kinesis.put_records(
        StreamName=input_stream_name,
        Records=[
            {
                "Data": payload,
                "PartitionKey": str(uuid.uuid4())
            } for payload in payloads])

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    retrieved_recs = []
    timeout = min(max(15, 4 * len(payloads)), 150)
    for si in shard_iterators:
        retrieved_recs += get_all_records(kinesis, si, len(payloads), timeout)

    assert len(retrieved_recs) == 2*len(payloads)
    retrieved_events = [json.loads(x["Data"].decode()) for x in retrieved_recs]
    retrieved_ids = {x["id"] for x in retrieved_events}
    put_ids = {json.loads(x)['id'] for x in payloads}
    assert not retrieved_ids.difference(put_ids)
    assert all("input_filter" in ev and "input_mapper" in ev
               and "receivedAt" in ev
               for ev in retrieved_events)


def test_set_get_state(
        environment, kinesis, payloads, shard_iterators, events,
        input_stream_name, output_stream_name):
    """Put and read a record from the input stream."""

    # Put the same record multiple times in the stream
    response = kinesis.put_records(
        StreamName=input_stream_name,
        Records=[
            {
                "Data": payloads[0],
                "PartitionKey": str(uuid.uuid4())
            } for _ in range(len(payloads))])

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    retrieved_recs = []
    timeout = min(max(15, 4 * len(payloads)), 150)
    for si in shard_iterators:
        retrieved_recs += get_all_records(kinesis, si, len(payloads), timeout)

    assert len(retrieved_recs) == 2
    retrieved_event = json.loads(retrieved_recs[0]["Data"].decode())
    retrieved_id = retrieved_event["id"]
    put_id = json.loads(payloads[0])["id"]
    assert put_id == retrieved_id
    assert "input_filter" in retrieved_event \
        and "input_mapper" in retrieved_event \
        and "receivedAt" in retrieved_event
