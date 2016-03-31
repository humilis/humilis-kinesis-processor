# -*- coding: utf-8 -*-

import uuid


def add_uuid(event):
    event["uuid"] = str(uuid.uuid4())
