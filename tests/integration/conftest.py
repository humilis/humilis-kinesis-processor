"""Global conftest."""
import pytest
from collections import namedtuple
import os
import time

import boto3
from humilis.environment import Environment


@pytest.fixture(scope="session")
def settings():
    """Global test settings."""
    Settings = namedtuple('Settings',
                          'stage environment_path streams_layer_name')
    return Settings(
        stage="DEV",
        environment_path="tests/integration/humilis-kinesis-processor.yaml.j2",
        streams_layer_name="streams")


@pytest.yield_fixture(scope="session")
def environment(settings):
    """The test environment: this fixtures creates it and takes care of
    removing it after tests have run."""
    env = Environment(settings.environment_path, stage=settings.stage)
    env.create()
    yield env
    env.delete()


@pytest.fixture(scope="session")
def output_stream_name(settings, environment):
    """The name of the output Kinesis stream."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return [(layer.outputs.get("OutputStream1"), 2),
            (layer.outputs.get("OutputStream2"), 1)]


@pytest.fixture(scope="session")
def input_stream_name(settings, environment):
    """The name of the output Kinesis stream."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return layer.outputs.get("InputStream")


@pytest.fixture(scope="session")
def kinesis():
    """Boto3 kinesis client."""
    region = os.environ.get("AWS_REGION") or "eu-west-1"
    return boto3.client("kinesis", region_name=region)


@pytest.fixture(scope="function")
def shard_iterators(kinesis, output_stream_name):
    """Get the latest shard iterator after emptying a shard."""
    sis = []
    for stream_name, nb_shards in output_stream_name:
        for shard in range(nb_shards):
            si = kinesis.get_shard_iterator(
                StreamName=stream_name,
                ShardId="shardId-{0:012d}".format(shard),
                ShardIteratorType="LATEST")["ShardIterator"]
            # At most 5 seconds to empty the shard
            for _ in range(10):
                kinesis_recs = kinesis.get_records(ShardIterator=si,
                                                   Limit=1000)
                si = kinesis_recs["NextShardIterator"]
                time.sleep(0.2)
            sis.append(si)

    return sis
