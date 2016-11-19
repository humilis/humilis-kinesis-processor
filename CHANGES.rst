Changelog
=========

0.9.7
-----

- Support for Lambda environment variables

0.9.6
-----

- Do not silence exception if Kinesis payload is not a json object

0.9.5
-----

- Support for delivery streams filters and mappers

0.9.0
-----

- Better debugging of processing errors

0.8.9
-----

- Add error annotations to events that failed to be processed

0.8.6
-----

- Bugfix in error handling logic.

0.8.5
-----

- Better error handling.

0.7.7
-----

- Support for multiple delivery streams for input, error, and output(s)

0.7.6
-----

- Support for one-to-many mappers

0.7.5
-----

- Users can also specify input/output/error streams by name instead of as
  references to another layer outputs.

0.6.8
-----

- Set environment variables for the humilis environment/layer/stage

0.4.0
-----

- Major bugfix: permission to put records in delivery streams

0.3.0
-----

- Major bugfix: give permission to write state to DynamodDB

0.2.0
-----

- Package becomes a generic map-multiplex-map processor (germangh)

0.1.1
-----

- Cleanup package data (bubenkoff)

0.1.0
-----

- Major refactoring to simplify and clean the code (germangh)

0.0.1
-----

- Initial release (bubenkoff)
