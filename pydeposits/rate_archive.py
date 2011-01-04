"""Stores and returns info about current and past currency rates."""

from decimal import Decimal
import datetime
import errno
import logging
import os
import sqlite3

from cl.core import Error

from pydeposits import cbrf
from pydeposits import constants
from pydeposits import sbrf
from pydeposits import util

LOG = logging.getLogger("pydeposits.rate_archive")


MIN_RATE_ACCURACY = 10
"""Minimum rate accuracy (in days).

In Russia we celebrate the new year for 10 days, so some banks may not provide
any info for this days.
"""

# TODO
ARCHIVE_PERIOD_AT_FIRST_START = 30
#ARCHIVE_PERIOD_AT_FIRST_START = 5 * 365
"""Number of days for which rate data will be downloaded at first start."""


class RateArchive:
    """Object that provides an ability to get currency rates info."""

    __db = None
    """Database for storing rate data."""

    __todays_rates = None
    """Rates for today."""


    def __init__(self):
        try:
            db_dir = os.path.expanduser("~/." + constants.APP_UNIX_NAME)
            db_path = os.path.join(db_dir, "rates.sqlite")

            try:
                os.makedirs(db_dir)
            except EnvironmentError, e:
                if e.errno != errno.EEXIST:
                    raise

            self.__db = sqlite3.connect(db_path)

            self.__db.execute("""
                CREATE TABLE IF NOT EXISTS rates (
                    day INTEGER,
                    currency TEXT,
                    sell_rate TEXT,
                    buy_rate TEXT
                )
            """)
            self.__db.execute("CREATE INDEX IF NOT EXISTS rate_index ON rates (day, currency)")
            self.__db.commit()
        except Exception, e:
            raise Error("Unable to open database '{0}':", db_path).append(e)

        try:
            self.__update()
        except Exception as e:
            raise Error("Unable to update rate info.").append(e)


    def __del__(self):
        if self.__db is not None:
            try:
                self.__db.close()
            except Exception, e:
                LOG.error(Error("Unable to close the database:").append(e))


    def get_approx(self, currency, date):
        """
        Returns currency rates for the specified date or for the nearest date
        if there is no data for the specified date.
        """

        if currency == constants.LOCAL_CURRENCY:
            return ( Decimal(1), Decimal(1) )

        day = util.get_day(date)

        rates = [ rate for rate in self.__db.execute("""
            SELECT
                day,
                sell_rate,
                buy_rate
            FROM
                rates
            WHERE
                currency = ? AND ? <= day <= ?
        """, (currency, day - MIN_RATE_ACCURACY, day + MIN_RATE_ACCURACY)) ]

        if (
            currency in self.__todays_rates and
            day - MIN_RATE_ACCURACY <= util.get_day(datetime.date.today()) <= day + MIN_RATE_ACCURACY
        ):
            rates.append(self.__todays_rates[currency])

        nearest = None
        for rate in rates:
            if nearest is None or abs(day - rate[0]) < abs(day - nearest[0]):
                nearest = rate

        if nearest is None:
            return None
        else:
            return ( Decimal(nearest[1]), Decimal(nearest[2]) )


    def __add(self, rates):
        """Saves new rate info."""

        data = []

        for date, currencies in rates.iteritems():
            for currency, rates in currencies.iteritems():
                data.append((
                    util.get_day(date),
                    currency, str(rates[0]), str(rates[1])
                ))

        self.__db.executemany("INSERT INTO rates VALUES (?, ?, ?, ?)", data)
        self.__db.commit()


    def __update(self):
        """Updates currency rate info."""

        last_date = self.__db.execute("SELECT MAX(day) FROM rates").fetchone()[0]

        if last_date:
            min_date = datetime.date.fromtimestamp(0) + datetime.timedelta(last_date + 1)
        else:
            LOG.info("Downloading currency rate archive. Please wait...")
            min_date = datetime.date.today() - datetime.timedelta(ARCHIVE_PERIOD_AT_FIRST_START)

        dates = []
        date = min_date
        today = datetime.date.today()
        while date <= today:
            dates.append(date)
            date += datetime.timedelta(1)

        rates = {}
        for source in (cbrf, sbrf):
            rates.update(source.get_rates(dates))
        self.__todays_rates = rates.pop(today, {})

        if rates:
            self.__add(rates)

