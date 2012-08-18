"""Contains tools for getting rate info from The Central Bank of the Russian Federation."""

from __future__ import unicode_literals

from decimal import Decimal
import logging
import urllib2
import xml.dom.minidom

from pycl.core import Error
from pydeposits import constants

LOG = logging.getLogger("pydeposits.cbrf")


def get_rates(dates):
    """Returns CBRF's rates for a specified dates."""

    rates = {}

    for date in dates:
        try:
            LOG.info("Getting CBRF's currency rates for %s...", date)

            url = "http://www.cbr.ru/scripts/XML_daily.asp?date_req=" \
                    "{0:02d}/{1:02d}/{2}".format(date.day, date.month, date.year)

            xml_contents = urllib2.urlopen(url, timeout = constants.NETWORK_TIMEOUT).read()
            dom = xml.dom.minidom.parseString(xml_contents)

            date_rates = {}

            for currency in dom.getElementsByTagName("Valute"):
                for node in currency.getElementsByTagName("CharCode")[0].childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        name = node.data
                        break
                else:
                    raise Error("Unable to get currency name.")

                for node in currency.getElementsByTagName("Value")[0].childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        rate = node.data
                        break
                else:
                    raise Error("Unable to get currency rate for {0}.", name)

                date_rates[name] = ( Decimal(rate.replace(",", ".")), ) * 2

            if not date_rates:
                raise Error("Empty XML document gotten.")

            rates[date] = date_rates
        except Exception as e:
            raise Error("Unable to get rate info from The Central Bank of the Russian Federation for {0}:", date).append(e)

    return rates
