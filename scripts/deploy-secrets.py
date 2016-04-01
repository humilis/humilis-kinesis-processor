#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Takes secrets from the local keyring and stores them in the secrets vault.
"""

import os
import sys

from humilis.environment import Environment
import keyring


# The namespace in the local keyring
NAMESPACE = "humilis-kinesis-mapper:{stage}"

# Map local secret keys to secret keys in the event tracker vault
SECRETS = {"sentry.dsn": "sentry.dsn"}


def deploy_secrets(environment_file, stage="dev"):
    """Deploy secrets to the secrets vault."""
    env = Environment(environment_file, stage=stage)

    print("Deploying secrets to environment vault ...")
    for local_key, vault_key in SECRETS.items():
        keychain_namespace = NAMESPACE.format(stage=stage.lower())
        value = keyring.get_password(keychain_namespace, local_key) or \
            os.environ.get("SENTRY_DSN")

        if value is None:
            print("Secret {}/{} not found in local keychain nor SENTRY_DSN "
                  "environment variable: skipping".format(keychain_namespace,
                                                          local_key))
        else:
            resp = env.set_secret(vault_key, value)
            status = resp['ResponseMetadata']['HTTPStatusCode']
            print("Setting secret '{}': [{}]".format(vault_key, status))


if __name__ == "__main__":
    deploy_secrets(*sys.argv[1:])
