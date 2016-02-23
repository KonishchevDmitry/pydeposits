# -*- coding: utf-8 -*-

"""Contains tools for getting rate info from Sberbank."""

import datetime
import logging
import re

from decimal import Decimal

import requests
from requests import RequestException

import xlrd
from xlrd import XL_CELL_EMPTY as EMPTY, XL_CELL_TEXT as TEXT, XL_CELL_NUMBER as NUMBER

from pydeposits.util import Error, fetch_url
from pydeposits.xls import RowNotFoundError, find_table, cmp_columns, cmp_column_types

log = logging.getLogger(__name__)


def get_rates(dates):
    """Returns Sberbank's rates for the specified dates."""

    rates = {}
    sources = (_CurrencyRates(), _MetalRates())

    for date in dates:
        for source in sources:
            day_rates = source.get_for_date(date)
            if day_rates:
                rates.setdefault(date, {}).update(day_rates)

    return rates


class _SberbankRates:
    __url_prefix = "http://data.sberbank.ru/"

    def __init__(self):
        super(_SberbankRates, self).__init__()
        self.__month_urls_cache = {}

    def get_for_date(self, date):
        if date < self._min_supported_date:
            return

        log.info("Getting Sberbank %s rates for %s...", self._name, date)

        day_urls = self._get_urls(date)
        if not day_urls:
            log.debug("There is no data for Sberbank %s rates for %s.", self._name, date)
            return

        for url_id, url in enumerate(day_urls):
            try:
                xls_contents = fetch_url(url).content
            except RequestException as e:
                if e.response is not None and e.response.status_code == requests.codes.not_found:
                    # It's a common error when we have 2 reports per day
                    (log.warning if url_id == len(day_urls) - 1 else log.debug)(
                        "Unable to download '%s': %s. Skipping it...", url, e)
                else:
                    raise Error("Failed to get Sberbank currency rates from {}: {}", url, e)
            else:
                break
        else:
            return

        try:
            rates = self.parse(xls_contents)
        except Exception as e:
            raise Error("Error while reading Sberbank currency rates obtained from {}: {}", url, e)

        log.debug("Gotten rates: %s", rates)

        return rates

    def _get_urls(self, date):
        month_id = (date.year, date.month)

        try:
            day_urls = self.__month_urls_cache[month_id]
        except KeyError:
            try:
                day_urls = self._get_month_urls(date)
            except Exception as e:
                raise Error("Unable to obtain a list of *.xls for {} rates for {:02d}.{}: {}",
                            self._name, date.month, date.year, e)

            self.__month_urls_cache[month_id] = day_urls

        return day_urls.get(date.day, [])

    def _get_month_urls(self, date):
        month_rates_url = "{prefix}moscow/ru/quotes/{archive}/index.php?year115={year}&month115={month}".format(
            prefix=self.__url_prefix, archive=self._sberbank_archive_name, year=date.year, month=date.month)

        rate_list_html = fetch_url(month_rates_url).text

        base_url = "/common/img/uploaded/banks/uploaded_mb/c_list/{}/download/".format(self._sberbank_rates_list_name)

        rate_url_matches = list(re.finditer(
            r'"(?P<url>' + re.escape(base_url) + r'(?P<year>\d{4})/(?P<upload_month>\d{2})/' +
            self._sberbank_rates_name + r'(?P<month>\d{2})(?P<day>\d{2})(_\d)?.xls)"', rate_list_html, re.VERBOSE))

        if not rate_url_matches:
            raise Error("Server returned an unexpected response.")

        day_urls = {}

        for match in rate_url_matches:
            rate_year, rate_month = int(match.group("year")), int(match.group("month"))

            if (rate_year, rate_month) != (date.year, date.month):
                # If we ask for data that Sberbank doesn't have it returns data for previous/current month/year.
                if not day_urls and _is_month_may_be_empty(date):
                    return day_urls

                raise Error("Server returned data for invalid month ({:02d}.{} instead of {:02d}.{}) on {}.",
                            rate_month, rate_year, date.month, date.year, month_rates_url)

            url = match.group("url")
            if "://" not in url:
                url = self.__url_prefix + url.lstrip("/")

            day_urls.setdefault(int(match.group("day")), []).append(url)

        return day_urls

    def parse(self, xls_contents):
        sheets = xlrd.open_workbook(file_contents=xls_contents).sheets()

        if len(sheets) == 0:
            raise Error("The *.xls file doesn't contain any sheet.")
        elif len(sheets) > 1:
            raise Error("The *.xls file contains more than one sheet.")

        return self._parse(sheets[0])


class _CurrencyRates(_SberbankRates):
    _name = "currency"
    _sberbank_archive_name = "archivecurrencies"
    _sberbank_rates_list_name = "vkurs"
    _sberbank_rates_name = "vk"
    _min_supported_date = datetime.date(2014, 5, 1)

    def _parse(self, sheet):
        try:
            _, row_id, column_id = find_table(sheet, (
                ("Курсы для проведения операций покупки и продажи наличной иностранной",),
                ("валюты за наличную валюту Российской Федерации:",),
                ("Наименование валют", "", "", "Масштаб", "Курс покупки", "Курс продажи"),
            ))
        except RowNotFoundError:
            raise Error("Unable to find rates table.")

        currencies = {
            "Доллар США": "USD_SBRF",
            "Евро":       "EUR_SBRF",
        }

        rates = {}

        while row_id < sheet.nrows:
            cell = sheet.cell(row_id, column_id)
            if cell.ctype == EMPTY:
                break

            if not cmp_column_types(sheet, row_id, column_id, (TEXT, EMPTY, EMPTY, NUMBER, NUMBER, NUMBER)):
                raise Error("Rates table validation failed.")

            try:
                currency_id = currencies[cell.value.strip()]
            except KeyError:
                pass
            else:
                scale = sheet.cell_value(row_id, column_id + 3)
                if scale != 1:
                    raise Error("Got {} rate with invalid scale: {}.", currency_id, scale)

                if currency_id in rates:
                    raise Error("Got a duplicated currency rates for {}.", currency_id)

                rates[currency_id] = tuple(
                    Decimal(value) for value in reversed(sheet.row_values(row_id, column_id + 4, column_id + 6)))

            row_id += 1

        missing_currencies = set(rates.keys()) - set(currencies.values())
        if missing_currencies:
            raise Error("Unable to find rates for the following currencies: {}.", ", ".join(missing_currencies))

        return rates


class _MetalRates(_SberbankRates):
    _name = "metal"

    _sberbank_archive_name = "archivoms"
    _sberbank_rates_list_name = "sdmet"
    _sberbank_rates_name = "dm"
    _min_supported_date = datetime.date(2013, 1, 1)

    def _parse(self, sheet):
        try:
            _, row_id, column_id = find_table(sheet, (
                ("3. Котировки продажи и покупки драгоценных металлов в обезличенном виде:",),
                ("Наименование драгоценного металла", "", "Продажа, руб. за грамм", "", "Покупка, руб. за грамм", ""),
            ))
        except RowNotFoundError:
            raise Error("Unable to find rates table.")

        rates = {}

        for row_id, (currency_id, currency_name) in enumerate((
            ("AUR_SBRF", "Золото"),
            ("AGR_SBRF", "Серебро"),
            ("PTR_SBRF", "Платина"),
            ("PDR_SBRF", "Палладий"),
        ), start=row_id):
            if (
                not cmp_columns(sheet, row_id, column_id, (currency_name,)) or
                not cmp_column_types(sheet, row_id, column_id, (TEXT, EMPTY, NUMBER, EMPTY, NUMBER, EMPTY))
            ):
                raise Error("Rates table validation failed.")

            rates[currency_id] = tuple(
                Decimal(value) for value in (sheet.cell_value(row_id, column_id + 2),
                                             sheet.cell_value(row_id, column_id + 4)))

        return rates


def _is_month_may_be_empty(date):
    # Month may be empty if it's only starting and there are
    # some holidays in the first days.

    today = datetime.date.today()

    return (
        (date.year, date.month) == (today.year, today.month) and (
            (today - datetime.date(today.year, today.month, 1)).days <= 2 or

            # Long New Year holidays
            today.month == 1 and (today - datetime.date(today.year, today.month, 1)).days <= 10 or

            # Long holidays in May
            today.month == 5 and (today - datetime.date(today.year, today.month, 1)).days <= 6
        )
    )
