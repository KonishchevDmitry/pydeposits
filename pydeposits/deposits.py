# -*- coding: utf-8 -*-

"""Provides functions for parsing deposit info specified by the user."""

from decimal import Decimal
import datetime
import imp
import pprint
import os

from cl.core import Error, LogicalError

from pydeposits import constants


def get():
    """Returns a list of deposits specified by the user."""

    info_path = os.path.join(os.path.expanduser("~/." + constants.APP_UNIX_NAME), "deposits.py")
    if not os.path.exists(info_path):
        raise Error(_NO_DEPOSIT_INFO_ERROR_MESSAGE.format(info_path))

    try:
        deposits = imp.load_source("pydeposits.deposits.deposit_info", info_path).deposits
        if not isinstance(deposits, list):
            raise Error("deposits variable must be a list of dictionaries")
    except Exception, e:
        raise Error("Failed to load deposit info from {0}:", info_path).append(e)

    fields = (
        ( "bank",            "string",  True  ),
        ( "open_date",       "date",    True  ),
        ( "close_date",      "date",    False ),
        ( "currency",        "string",  True  ),
        ( "source_currency", "string",  False ),
        ( "amount",          "decimal", True  ),
        ( "interest",        "decimal", False ),
        ( "capitalization",  "decimal", False ),
    )

    field_names = set()
    for field in fields:
        field_names.add(field[0])

    for deposit in deposits:
        try:
            if not isinstance(deposit, dict):
                raise Error("it is not a dictionary")

            if set(deposit.keys()).difference(field_names):
                raise Error("unknown field")

            for field_name, type_name, required in fields:
                if field_name not in deposit:
                    if required:
                        raise Error("there is no required field {0}", field_name)
                    else:
                        continue

                if type_name == "string":
                    deposit[field_name] = (deposit[field_name])
                elif type_name == "date":
                    deposit[field_name] = datetime.datetime.strptime(deposit[field_name], "%d.%m.%Y").date()
                elif type_name == "decimal":
                    deposit[field_name] = Decimal(str(deposit[field_name]))
                else:
                    raise LogicalError()
        except Exception, e:
            raise Error("Invalid deposit info:\n{0}", pprint.pformat(deposit))

    if not deposits:
        raise Error("You specified an empty deposit list.")

    return deposits


_NO_DEPOSIT_INFO_ERROR_MESSAGE = u"""\
You haven't specified any deposit info.

Please create file {0} and fill it up with information about your deposits. It
should be an ordinary Python file with global deposits variable.

For example:

# -*- coding: utf-8 -*-

# Required fields:
# * bank            - the bank name
# * open_date       - the date when the deposit was opened
# * close_date      - the date when the deposit will be closed (optional)
# * currency        - currency of the deposit. May be RUR, USD, EUR, etc +
#                     AUR_SBRF, AGR_SBRF, PTR_SBRF and PDR_SBRF for Sberbank's
#                     deposits in gold, silver, platinum and palladium.
# * source_currency - currency in which your money was before the deposit was
#                     opened. If it is not specified, the currency field's
#                     value will be gotten. It is needed to calculate your
#                     profit or loss depending on fluctuation of currency
#                     rates.
# * amount          - amount of money on the deposit in the specified currency
# * interest        - the deposit's interest
# * capitalization  - You must specify capitalization field if your deposit has
#                     capitalization option. The value is a number of months
#                     after which capitalization occurs for this deposit.


deposits = [{{
    "bank":            u"МКБ",
    "open_date":       "06.12.2010",
    "close_date":      "06.06.2011",
    "currency":        "RUR",
    "amount":          100000,
    "interest":        9.75,
    "capitalization":  1
}},{{
    "bank":            u"РОСТ",
    "open_date":       "19.11.2010",
    "close_date":      "22.05.2011",
    "source_currency": "RUR",
    "currency":        "EUR",
    "amount":          2000,
    "interest":        7
}},{{
    "bank":            u"Сбербанк",
    "open_date":       "12.10.2009",
    "currency":        "AUR_SBRF",
    "amount":          100,
    "source_currency": "RUR"
}}]"""

