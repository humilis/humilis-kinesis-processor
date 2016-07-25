
import uuid

from lambdautils.monitor import graphite_monitor
import lambdautils.state as state


def partition_key(event):
    return event.get("client_id", str(uuid.uuid4()))


@graphite_monitor("processed.events")
def input_filter(event, *args, **kwargs):
    event["input_filter"] = True
    id = event.get("id")
    if state.get_state(id):
        return False
    else:
        state.set_state(id, "hello there")

    return True


def output_filter_1(event, *args, **kwargs):
    event["output_filter_1"] = True
    return True


def output_mapper_1(event, *args, **kwargs):
    event["output_mapper_1"] = True
    return event


def output_mapper_2(event, *args, **kwargs):
    event["output_mapper_2"] = True
    return event


def error_filter(event, *args, **kwargs):
    print(event)
    return True


def error_mapper(event, *args, **kwargs):
    print(event)
    return event
