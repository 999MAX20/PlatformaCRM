"""Read-only platform snapshots: missing sources stay unknown, never zero.

A savepoint also keeps other sources readable after a PostgreSQL statement error
inside a request/test transaction. Never expose the exception text to the API.
"""
from django.db import DatabaseError, transaction


def read_platform_source(read, *, unavailable=None):
    try:
        with transaction.atomic():
            return read()
    except DatabaseError:
        return unavailable
