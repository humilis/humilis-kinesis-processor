Kinesis event stream processor
===================================

.. |Build Status| image:: https://travis-ci.org/humilis/humilis-kinesis-processor.svg?branch=master
   :target: https://travis-ci.org/humilis/humilis-kinesis-processor
.. |PyPI| image:: https://img.shields.io/pypi/v/humilis-kinesis-processor.svg?style=flat
   :target: https://pypi.python.org/pypi/humilis-kinesis-processor

|Build Status| |PyPI|

A `humilis <https://github.com/humilis/humilis>`__ plugin to deploy a
`Lambda <https://aws.amazon.com/documentation/lambda/>`__ function that
maps events in a `Kinesis <https://aws.amazon.com/documentation/kinesis/>`__
event stream using a list of Python callables.

Installation
------------

::

    pip install humilis-kinesis-processor

Development
-----------

Assuming you have
`virtualenv <https://virtualenv.readthedocs.org/en/latest/>`__ installed:

::

    make develop

Configure humilis:

::

    .env/bin/humilis configure --local

Testing
-------

Unit tests
~~~~~~~~~~

To run the local test suite:

::

    make test


Integration tests
~~~~~~~~~~~~~~~~~

Before running the integration test suite you need to set a few deployment 
secrets using the command::

..code:: bash

    s3keyring set [group]:[STAGE] [key] [secret]

In group ``humilis-kinesis-processor`` the following secrets need to be set:

* ``sentry.dsn``: The `Sentry DSN <https://docs.getsentry.com/hosted/quickstart/#configure-the-dsn>`__.


By the default, the integration tests will deploy on a stage called ``DEV`` so
the command to set the Sentry DSN is::

..code:: bash

    s3keyring set humilis-kinesis-processor:DEV sentry.dsn [SENTRYDSN]


To run the integration test suite::

.. code:: bash

    make testi

The command above will deploy a Kinesis processor to your AWS account, and will
also create additional resources (such as several Kinesis streams) needed to
test that the deployment was successful. Once deployed, the integration tests
will run, and once they have completed the test environment will be destroyed.

If you do not want the test environment to be destroyed after tests have 
completed you should run instead::

.. code:: bash

    make testi DESTROY=no

You can also modify the name of the deployment stage by setting the ``STAGE``
environment variable. For instance, to deploy to a ``TEST`` stage:

.. code:: bash

    make testi STAGE=TEST



More information
----------------

See `humilis <https://github.com/humilis/humilis>`__ documentation.


Contact
-------

If you have questions, bug reports, suggestions, etc. please create an issue on
the `GitHub project page <http://github.com/humilis/humilis-kinesis-processor>`_.

License
-------

This software is licensed under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_

See `License file <https://github.com/humilis/humilis-kinesis-processor/blob/master/LICENSE.txt>`_


© 2016 Anatoly Bubenkov, `FindHotel <http://company.findhotel.net>`_ and others.
