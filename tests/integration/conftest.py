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
        environment_path="tests/integration/humilis-kinesis-mapper.yaml.j2",
        streams_layer_name="streams")


@pytest.fixture(scope="session")
def environment(settings):
    """The lambda-processor-test humilis environment."""
    env = Environment(settings.environment_path, stage=settings.stage)
    return env


@pytest.fixture(scope="session")
def io_stream_names(settings, environment):
    """The name of the input and output streams in the rawpipe layer."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return (layer.outputs.get("InputStream"),
            layer.outputs.get("OutputStream"),
            layer.outputs.get("ErrorStream"))


@pytest.fixture(scope="session")
def kinesis():
    """Boto3 kinesis client."""
    region = os.environ.get("AWS_REGION") or "eu-west-1"
    return boto3.client("kinesis", region_name=region)


@pytest.fixture(scope="function")
def shard_iterators(kinesis, io_stream_names):
    """Get the latest shard iterator after emptying a shard."""
    sis = []
    for stream_name in io_stream_names:
        si = kinesis.get_shard_iterator(
            StreamName=stream_name,
            ShardId="shardId-000000000000",     # Only 1 shard
            ShardIteratorType="LATEST")["ShardIterator"]
        # At most 5 seconds to empty the shard
        for _ in range(10):
            kinesis_recs = kinesis.get_records(ShardIterator=si, Limit=10000)
            si = kinesis_recs["NextShardIterator"]
            time.sleep(0.2)
        sis.append(si)
    return sis
