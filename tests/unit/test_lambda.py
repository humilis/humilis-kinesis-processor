"""Test the logic of the Lambda function."""
from mock import Mock

from humilis_kinesis_mapper.lambda_function.processor.main import process_event


def test_process_event(kinesis_event, event, context, boto3_client, monkeypatch):
    """Process events."""
    cal = Mock()
    process_event(kinesis_event, context, "input", "input_delivery", "output_delivery", [cal])
    # The processor should have inserted the records in the output stream
    assert boto3_client("kinesis").put_records.call_count == 1
    cal.assert_called_once_with(event)
