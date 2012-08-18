"""Contains various utils."""

from __future__ import unicode_literals

import datetime

def get_day(date):
    """Converts a date to day number from UNIX epoch."""

    return (date - datetime.date.fromtimestamp(0)).days
