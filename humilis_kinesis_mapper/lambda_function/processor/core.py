# -*- coding: utf-8 -*-

import json
import logging

# preprocessor:jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def transform_events(events, callables):
    """Parses the user agents."""
    for event in events:
        logger.info("Input event: {}".format(json.dumps(event, indent=4)))
        for cal in callables:
            cal(event)
        logger.info("Mapped event: {}".format(json.dumps(event, indent=4)))

    return events
