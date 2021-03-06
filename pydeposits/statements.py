"""Provides a tools for getting deposit statements."""

import copy
import datetime
import time

from decimal import Decimal

from pcli.text_table import Table, Column

import pydeposits.constants as constants
from pydeposits.rate_archive import RateArchive
from pydeposits.util import Error


def print_account_statement(holdings, today, show_all):
    """Prints out current deposit statement."""

    table = Table([
        Column("expired",             "Expiration",         align=Column.ALIGN_CENTER, hide_if_empty=True),
        Column("open_date_string",    "Open date",          align=Column.ALIGN_CENTER                    ),
        Column("close_date_string",   "Close date",         align=Column.ALIGN_CENTER                    ),
        Column("closed",              "Closed",             align=Column.ALIGN_CENTER, hide_if_empty=True),
        Column("bank",                "Bank",               align=Column.ALIGN_CENTER                    ),
        Column("currency",            "Currency",           align=Column.ALIGN_CENTER                    ),
        Column("amount",              "Amount"                                                           ),
        Column("cost",                "Cost"                                                             ),
        Column("interest",            "Interest"                                                         ),
        Column("rate_profit",         "Rate profit"                                                      ),
        Column("current_amount",      "Current amount"                                                   ),
        Column("current_cost",        "Current cost"                                                     ),
        Column("pure_profit",         "Pure profit"                                                      ),
        Column("pure_profit_percent", "Pure profit persent"                                              ),
    ])

    holdings = copy.deepcopy(holdings)
    holdings.sort(key=_holding_cmp_key)

    total = Decimal(0)
    total_profit = Decimal(0)
    current_total = Decimal(0)

    for holding in holdings:
        opened = not holding.get("closed", False)
        expired = ( holding.get("close_date", today) < today )

        if today < holding["open_date"] or not show_all and not opened:
            continue

        holding["open_date_string"] = holding["open_date"].strftime(constants.DATE_FORMAT)
        if "close_date" in holding:
            holding["close_date_string"] = holding["close_date"].strftime(constants.DATE_FORMAT)

            if expired:
                holding["expired"] = "Expired"

        _calculate_holding_info(holding, holding["close_date"] if expired else today)

        if opened:
            total += holding.get("cost", 0)
            current_total += holding.get("current_cost", 0)
            total_profit += holding.get("pure_profit", 0)

        for key in ("amount", "cost", "rate_profit", "current_amount", "current_cost", "pure_profit"):
            if key in holding:
                holding[key] = _round_normal(holding[key])

        for key in ("interest", "pure_profit_percent"):
            if key in holding:
                holding[key] = _round_precise(holding[key])

        holding["closed"] = "" if opened else "x"
        table.add_row(holding)

    table.add_row({})
    table.add_row({
        "cost":         _round_normal(total),
        "current_cost": _round_normal(current_total),
        "pure_profit":  _round_normal(total_profit),
    })

    print(); table.draw("Account statement for {0}:".format(today))


def print_expiring(holdings, today, days):
    """Prints out holdings that will be expired in specified number of days."""

    expiring = []

    for holding in sorted(holdings, key=_holding_cmp_key, reverse=True):
        if (
            not holding.get("closed", False) and
            "close_date" in holding and
            holding["close_date"] <= today + datetime.timedelta(days)
        ):
            expiring.append(holding)

    if expiring:
        print("Following deposits will be expired in {0} days:".format(days))

        for holding in expiring:
            print("  * {0} {1} ({2})".format(
                holding["close_date"].strftime(constants.DATE_FORMAT),
                holding["bank"], holding["currency"]))


def _calculate_current_amount(holding, today):
    """Calculates current amount and profit on a holding."""

    open_date = holding["open_date"]

    if "close_date" in holding and holding["close_date"] < today:
        to_date = holding["close_date"]
    else:
        to_date = today

    per_day = holding.get("interest", Decimal(0)) / 100 / _days_in_year(open_date.year)

    profit = 0
    amount = holding["amount"]

    month = -1
    cur_date = open_date
    next_date = cur_date
    completions = holding.get("completions", [])[:]

    while True:
        if next_date > to_date:
            next_date = to_date

        if completions:
            while cur_date <= next_date:
                while completions and completions[0]["date"] == cur_date:
                    completion = completions.pop(0)
                    amount += completion["amount"]

                if cur_date == next_date:
                    break

                profit += amount * per_day
                cur_date += datetime.timedelta(1)
        else:
            profit += amount * per_day * (next_date - cur_date).days
            cur_date = next_date

        if cur_date == to_date:
            amount += profit
            break

        month += 1
        if "capitalization" in holding and month and month % holding["capitalization"] == 0:
            amount += profit
            profit = 0

        next_date_year = cur_date.year
        next_date_month = cur_date.month + 1
        if next_date_month > 12:
            next_date_year += 1
            next_date_month = 1
        next_date_day = open_date.day

        while True:
            try:
                next_date = datetime.date(next_date_year, next_date_month, next_date_day)
            except ValueError:
                next_date_day -= 1
                if next_date_day < 0:
                    raise Error("Logical error.")
            else:
                break

    holding["current_amount"] = amount


def _calculate_current_cost(holding, today):
    """Calculates current cost of a holding (in a local currency)."""

    rate_archive = RateArchive()
    cur_rates = rate_archive.get_approx(holding["currency"], today)
    if cur_rates is not None:
        # TODO: bank interest
        holding["current_cost"] = holding["current_amount"] * cur_rates[1]


def _calculate_holding_info(holding, today):
    """Calculates various info about a holding."""

    _calculate_past_cost(holding, today)
    _calculate_rate_profit(holding, today)
    _calculate_current_amount(holding, today)
    _calculate_current_cost(holding, today)
    _calculate_pure_profit(holding, today)


    rate_archive = RateArchive()

    for completion in holding.get("completions", []):
        if completion["date"] <= today:
            holding["amount"] += completion["amount"]

    cur_rates = rate_archive.get_approx(holding["currency"], today)
    if cur_rates is not None:
        holding["cost"] = holding["amount"] * cur_rates[1]


def _calculate_past_cost(holding, today):
    """
    Calculates cost of a holding (in a local currency) for the time, when it
    was opened.
    """

    source_currency = holding.get("source_currency", holding["currency"])

    if source_currency == constants.LOCAL_CURRENCY and holding["currency"] == constants.LOCAL_CURRENCY:
        holding["past_cost"] = holding["amount"]
    elif source_currency == constants.LOCAL_CURRENCY and "source_amount" in holding:
        holding["past_cost"] = holding["source_amount"]
    else:
        past_rates = RateArchive().get_approx(holding["currency"], holding["open_date"])

        if past_rates is not None:
            if source_currency == constants.LOCAL_CURRENCY:
                holding["past_cost"] = past_rates[0] * holding["amount"]
            elif source_currency == holding["currency"]:
                holding["past_cost"] = past_rates[1] * holding["amount"]
            else:
                # TODO FIXME
                raise Error("Not supported")

    for completion in holding.get("completions", []):
        if completion["date"] <= today:
            if holding["currency"] == constants.LOCAL_CURRENCY:
                holding["past_cost"] += completion["amount"]
            else:
                # TODO FIXME
                raise Error("Not supported")


def _calculate_pure_profit(holding, today):
    """Calculates pure profit from a holding for today."""

    if "past_cost" in holding and "current_cost" in holding:
        holding["pure_profit"] = holding["current_cost"] - holding["past_cost"]

        if "completions" not in holding:
            # TODO ?
            if holding["past_cost"] == 0 or today == holding["open_date"]:
                holding["pure_profit_percent"] = Decimal(0)
            else:
                holding["pure_profit_percent"] = (holding["pure_profit"] / holding["past_cost"]) * 100 \
                                                 / (today - holding["open_date"]).days * _days_in_year(today.year)


def _calculate_rate_profit(holding, today):
    """Calculates rate profit for a holding."""

    source_currency = holding.get("source_currency", holding["currency"])

    if (
        (source_currency != constants.LOCAL_CURRENCY or holding["currency"] != constants.LOCAL_CURRENCY) and
        "past_cost" in holding
    ):
        cur_rates = RateArchive().get_approx(holding["currency"], today)

        if cur_rates is not None:
            holding["rate_profit"] = cur_rates[1] * holding["amount"] - holding["past_cost"]


def _days_in_year(year):
    """Returns number of days in a year."""

    return 366 if _is_leap_year(year) else 365


def _holding_cmp_key(holding):
    """Compares two holdings (for printing them out)."""

    return (
        "close_date" in holding,
        -time.mktime(holding.get("close_date", datetime.date.today()).timetuple()),
        holding["bank"]
    )


def _is_leap_year(year):
    """Returns True if year is a leap year."""

    if year % 400 == 0:
        return True
    elif year % 100 == 0:
        return False
    elif year % 4 == 0:
        return True
    else:
        return False


def _round_normal(value):
    """Rounds an integer with ordinary precision."""

    if value is not None:
        return value.quantize(Decimal('0'))


def _round_precise(value):
    """Rounds an integer with high precision."""

    if value is not None:
        return value.quantize(Decimal('0.00'))
