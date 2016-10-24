"""Integration test suite utilities."""

import time


def get_all_records(client, sharditer, limit, timeout=10):
    """Retrieve all records from a Kinesis stream."""
    retrieved_recs = []
    for _ in range(timeout):
        kinesis_recs = client.get_records(ShardIterator=sharditer, Limit=limit)
        sharditer = kinesis_recs["NextShardIterator"]
        retrieved_recs += kinesis_recs["Records"]
        if len(retrieved_recs) == limit:
            # All records have been retrieved
            break
        time.sleep(1)

    return retrieved_recs


def get_shard_iterators(kinesis, stream):
    """Get the latest shard iterator(s) after emptying a shard."""
    sis = []
    for stream_name, nb_shards in stream:
        for shard in range(nb_shards):
            sharditer = kinesis.get_shard_iterator(
                StreamName=stream_name,
                ShardId="shardId-{0:012d}".format(shard),
                ShardIteratorType="LATEST")["ShardIterator"]
            # At most 2 seconds to empty the shard
            for _ in range(20):
                kinesis_recs = kinesis.get_records(ShardIterator=sharditer,
                                                   Limit=1000)
                sharditer = kinesis_recs["NextShardIterator"]
                time.sleep(0.2)
            sis.append(sharditer)

    return sis
