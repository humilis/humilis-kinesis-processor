# -*- coding: utf-8 -*-

# preprocessor:jinja2


def transform_events(events, callables, environment, layer, stage, shard_id):
    """Transforms events with the given callables."""

    for event in events:
        for cal in callables:
            cal(event, environment=environment, layer=layer, stage=stage,
                shard_id=shard_id)

    return events
