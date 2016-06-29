"""A sample module that contains a mapper function."""


def input_mapper(event, *args, **kwargs):
    event["input_mapper"] = True
