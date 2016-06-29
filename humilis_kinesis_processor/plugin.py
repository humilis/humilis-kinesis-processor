"""Humilis plugin entrypoint."""

import os


def get_layer_path():
    """Get the layer config templates path."""
    return os.path.dirname(__file__)
