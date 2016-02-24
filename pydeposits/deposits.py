# -*- coding: utf-8 -*-

"""Provides functions for parsing deposit info specified by the user."""

import datetime
import imp
import pprint
import os

from decimal import Decimal

from pydeposits import constants
from pydeposits.util import Error


def get():
    """Returns a list of deposits specified by the user."""

    info_path = os.path.join(os.path.expanduser("~/." + constants.APP_UNIX_NAME), "deposits.py")
    if not os.path.exists(info_path):
        raise Error(_NO_DEPOSIT_INFO_ERROR_MESSAGE, info_path)

    try:
        deposits = imp.load_source("pydeposits.deposits.deposit_info", info_path).deposits
        if not isinstance(deposits, list):
            raise Error("deposits variable must be a list of dictionaries")
    except Exception as e:
        raise Error("Failed to load deposit info from {}:", info_path).append(e)

    fields = (
        ("bank",            "string",  True ),
        ("open_date",       "date",    True ),
        ("close_date",      "date",    False),
        ("currency",        "string",  True ),
        ("source_currency", "string",  False),
        ("amount",          "decimal", True ),
        ("source_amount",   "decimal", False),
        ("interest",        "decimal", False),
        ("capitalization",  "decimal", False),
        ("completions",     "",        False),
        ("closed",          "bool",    False),
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
                        raise Error("there is no required field {}", field_name)
                    else:
                        continue

                if field_name == "completions":
                    completion_fields = {"date", "amount"}

                    if not isinstance(deposit["completions"], list):
                        raise Error("Invalid field type.")

                    for completion in deposit["completions"]:
                        if set(completion.keys()).difference(completion_fields):
                            raise Error("Unknown field")

                        completion["date"] = datetime.datetime.strptime(completion["date"], constants.DATE_FORMAT).date()
                        completion["amount"] = Decimal(str(completion["amount"]))
                elif type_name == "string":
                    pass
                elif type_name == "bool":
                    if not isinstance(deposit[field_name], bool):
                        raise Error("Invalid field type.")
                elif type_name == "date":
                    deposit[field_name] = datetime.datetime.strptime(deposit[field_name], constants.DATE_FORMAT).date()
                elif type_name == "decimal":
                    deposit[field_name] = Decimal(str(deposit[field_name]))
                else:
                    raise Error("Logical error.")

            if "source_amount" in deposit and "source_currency" not in deposit:
                raise Error("`source_currency` must be specified when `source_amount` is specified.")

            if "completions" in deposit:
                for completion in deposit["completions"]:
                    if(
                        completion["date"] < deposit["open_date"] or
                        "close_date" in deposit and completion["date"] >= deposit["close_date"]
                    ):
                        raise Error("Invalid completion date.")

                deposit["completions"].sort(key=lambda completion: completion["date"])
        except Exception:
            raise Error("Invalid deposit info:\n{}", pprint.pformat(deposit))

    if not deposits:
        raise Error("You specified an empty deposit list.")

    return deposits


_NO_DEPOSIT_INFO_ERROR_MESSAGE = """\
You haven't specified any deposit info.

Please create file {0} and fill it up with information about your deposits. It
should be an ordinary Python file with global deposits variable.

For example:

# -*- coding: utf-8 -*-

# Fields:
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
# * source_amount   - amount of money in the source currency that was converted
#                     into the deposit's currency
# * interest        - the deposit's interest
# * capitalization  - You must specify capitalization field if your deposit has
#                     capitalization option. The value is a number of months
#                     after which capitalization occurs for this deposit.
# * completions     - A list of completions that has been committed after
#                     opening the deposit.
# * closed          - True if the deposit is already closed.


deposits = [{{
    "bank":            "МКБ",
    "open_date":       "06.12.2010",
    "close_date":      "06.06.2011",
    "currency":        "RUR",
    "amount":          100000,
    "interest":        "9.75",
    "capitalization":  1
}},{{
    "bank":            "РОСТ",
    "open_date":       "19.11.2010",
    "close_date":      "22.05.2011",
    "source_currency": "RUR",
    "currency":        "EUR",
    "amount":          2000,
    "interest":        7,
    "completions":     [{{
        "date":   "08.12.2010",
        "amount": 100
    }},{{
        "date":   "02.03.2011",
        "amount": 250
    }}]
}},{{
    "bank":            "Сбербанк",
    "open_date":       "12.10.2009",
    "currency":        "AUR_SBRF",
    "amount":          100,
    "source_currency": "RUR"
}}]"""
