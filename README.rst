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

To run the local test suite:

::

    make test

You can test the deployment of the Lambda function using:

.. code:: bash

    make create

The command above will also create additional resources (such as several
Kinesis streams) needed to test that the deployment was successful. Once
deployed you can run the integration test suite using:

::

    make testi

Don't forget to delete the test deployment after you are done:

.. code:: bash

    make delete

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
