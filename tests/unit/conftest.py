"""Unit tests fixtures and utilities."""
from __future__ import unicode_literals

import uuid

from mock import Mock
import pytest


@pytest.fixture
def kinesis_record_template():
    """Template for a Kinesis event data record."""
    return {
        "eventID": "shardId-000000000000:44200961",
        "eventVersion": "1.0",
        "kinesis": {
            "partitionKey": "partitionKey-3",
            "data": "",
            "kinesisSchemaVersion": "1.0",
            "sequenceNumber": "4954511524144582180062593244200961"
        },
        "invokeIdentityArn": "arn:aws:iam::EXAMPLE",
        "eventName": "aws:kinesis:record",
        "eventSourceARN": "arn:aws:kinesis:EXAMPLE",
        "eventSource": "aws:kinesis",
        "awsRegion": "us-east-1"}


@pytest.fixture(scope="session")
def context():
    """A dummy AWS Lambda context object."""
    class DummyContext(object):

        """Dummy AWS Context object."""

        def __init__(self):
            self.data = {
                "function_name": "dummy_name",
                "function_version": 1,
                "invoked_function_arn": "arn",
                "memory_limit_in_mb": 128,
                "aws_request_id": str(uuid.uuid4()),
                "log_group_name": "dummy_group",
                "log_stream_name": "dummy_stream",
                "identity": Mock(return_value=None),
                "client_context": Mock(return_value=None)}

        def __getattr__(self, name):
            """Get class attributes."""
            return self.data.get(name)

        @staticmethod
        def get_remaining_time_in_millis():
            """Get remaining time for the current AWS Lambda invocation."""
            return 100

    return DummyContext()


@pytest.fixture
def kms_client():
    """Mocked boto3 DynamoDB client."""
    mocked = Mock()
    mocked.decrypt = Mock(return_value={"Plaintext": b"dummy"})
    return mocked


@pytest.fixture
def kinesis_client():
    """Mocked boto3 Kinesis client."""
    mocked = Mock()
    ok_resp = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mocked.put_records = Mock(return_value=ok_resp)
    mocked.put_record_batch = Mock(return_value=ok_resp)
    return mocked


@pytest.fixture
def dynamodb_resource():
    """Mocked boto3 DynamoDB resource."""
    mock_item = Mock()
    mock_item.value = "encrypted"
    mock_item.get = Mock(return_value=None)
    return_value = {"Item": mock_item}
    mocked_table = Mock()
    mocked_table.get_item = Mock(return_value=return_value)
    mocked = Mock()
    mocked.Table = Mock(return_value=mocked_table)
    return mocked


@pytest.fixture
def dynamodb_client():
    """Mocked DynamoDB client."""
    mocked = Mock()
    return_value = {"Item": {"value": {"B": "encrypted"}}}
    mocked.get_item = Mock(return_value=return_value)
    mocked.decrypt = Mock(return_value={"Plaintext": b"dummy"})
    return mocked


@pytest.fixture
def boto3_client(kinesis_client, kms_client, dynamodb_client):
    """Mocked boto3.client."""
    def produce_client(name):
        """Produce boto3.client mock."""
        return {"kinesis": kinesis_client, "kms": kms_client,
                "firehose": kinesis_client,
                "dynamodb": dynamodb_client}[name]

    mocked = Mock(side_effect=produce_client)
    return mocked


@pytest.fixture
def boto3_resource(dynamodb_resource):
    """Mocked boto3.resource."""
    def produce_resource(name):
        """Produce DynamoDB resource mock."""
        return {"dynamodb": dynamodb_resource}[name]

    mocked = Mock(side_effect=produce_resource)
    return mocked


@pytest.fixture(autouse=True)
def global_patch(boto3_client, boto3_resource, monkeypatch):
    """Patch boto3."""
    monkeypatch.setattr("boto3.client", boto3_client)
    monkeypatch.setattr("boto3.resource", boto3_resource)
