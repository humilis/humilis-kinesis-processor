Kinesis event stream mapper
===================================

.. |Build Status| image:: https://travis-ci.org/humilis/humilis-kinesis-mapper.svg?branch=master
   :target: https://travis-ci.org/humilis/humilis-kinesis-mapper
.. |PyPI| image:: https://img.shields.io/pypi/v/humilis-kinesis-mapper.svg?style=flat
   :target: https://pypi.python.org/pypi/humilis-kinesis-mapper

|Build Status| |PyPI|

A `humilis <https://github.com/humilis/humilis>`__ plugin to deploy a
`Lambda <https://aws.amazon.com/documentation/lambda/>`__ function that
maps events in a `Kinesis <https://aws.amazon.com/documentation/kinesis/>`__
event stream using a list of Python callables.

Installation
------------

::

    pip install humilis-kinesis-mapper

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
the `GitHub project page <http://github.com/humilis/humilis-kinesis-mapper>`_.

License
-------

This software is licensed under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_

See `License file <https://github.com/humilis/humilis-kinesis-mapper/blob/master/LICENSE.txt>`_


© 2016 Anatoly Bubenkov, Innovative Travel and others.
