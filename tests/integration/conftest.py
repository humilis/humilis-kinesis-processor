"""Integration tests conftest."""

from collections import namedtuple
import os
import time

import pytest

import boto3
from humilis.environment import Environment
from s3keyring.s3 import S3Keyring

keyring = S3Keyring(config_file=".s3keyring.ini")


@pytest.fixture(scope="session")
def settings():
    """Global test settings."""
    Settings = namedtuple('Settings',
                          'stage environment_path streams_layer_name '
                          'output_path')
    envfile = "tests/integration/humilis-kinesis-processor"
    stage = os.environ.get("STAGE", "DEV")
    return Settings(
        stage=stage,
        environment_path="{}.yaml.j2".format(envfile),
        output_path="{}-{}.outputs.yaml".format(envfile, stage),
        streams_layer_name="streams")


@pytest.yield_fixture(scope="session")
def environment(settings):
    """The test environment: this fixtures creates it and takes care of
    removing it after tests have run."""
    env = Environment(settings.environment_path, stage=settings.stage)
    if os.environ.get("UPDATE", "yes") == "yes":
        env.create(update=True, output_file=settings.output_path)
    else:
        env.create(output_file=settings.output_path)

    val = keyring.get_password(
        "humilis-kinesis-processor/{}".format(settings.stage), "sentry/dsn")
    env.set_secret("sentry.dsn", val)
    yield env
    if os.environ.get("DESTROY", "yes") == "yes":
        # Empty the S3 bucket
        bucket = env.outputs["storage"]["BucketName"]
        os.system("aws s3 rm s3://{} --recursive".format(bucket))
        env.delete()


@pytest.fixture(scope="session")
def output_stream_name(settings, environment):
    """The name of the output Kinesis stream."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return [(layer.outputs.get("OutputStream1"), 2),
            (layer.outputs.get("OutputStream2"), 1)]


@pytest.fixture(scope="session")
def error_stream_name(settings, environment):
    """The name of the error Kinesis stream."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return [(layer.outputs.get("ErrorStream"), 1)]


@pytest.fixture(scope="session")
def input_stream_name(settings, environment):
    """The name of the output Kinesis stream."""
    layer = [l for l in environment.layers
             if l.name == settings.streams_layer_name][0]
    return layer.outputs.get("InputStream")


@pytest.fixture(scope="session")
def kinesis():
    """Boto3 kinesis client."""
    region = os.environ.get("AWS_DEFAULT_REGION") or "eu-west-1"
    return boto3.client("kinesis", region_name=region)


