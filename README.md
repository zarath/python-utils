Python utils
============

Repository for small scriplets with generic usability

Limiter
-------

Have you ever been forced to ensure that a program or
program group will only be called at maximum n-times
in a given timerange?

Then limiter.py provides a solution for this problem.
Program calls are tracked in a berkeley db which can
be shared between multiple scripts.

The library can be used as command line, pipe or as
python library.
