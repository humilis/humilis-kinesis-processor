#!/usr/bin/env python
"""Empty the test environment bucket."""

import os
import sys
import yaml


def empty_bucket(outputs_file):
    """Empty the bucket associated to the test deployment."""

    if not os.path.isfile(outputs_file):
        print("Environment outputs not found: cannot empty bucket")
        return
    with open(outputs_file, "r") as f:
        outputs = yaml.load(f)

    bucket = outputs["storage"]["BucketName"]

    print("Emptying bucket {} ...".format(bucket))
    os.system("aws s3 rm s3://{} --recursive".format(bucket))
    print("Bucket {} has been emptied".format(bucket))

if __name__ == "__main__":
    empty_bucket(*sys.argv[1:])
