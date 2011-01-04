# -*- coding: utf-8 -*-

"""Contains tools for getting info from Sberbank Russia."""

import urllib2

import xlrd

CURRENCIES = set((
    "AUR_SBRF",
    "AGR_SBRF",
    "PTR_SBRF",
    "PDR_SBRF"
))
"""Currencies supported by the module."""

NETWORK_TIMEOUT = 30
"""Network timeout in seconds."""


def get_rates(currencies, dates):
    """Returns Sberbank's rates for a specified dates."""

    currencies = set(currencies)

    not_found = currencies.difference(CURRENCIES)
    if not_found:
        raise Exception("Invalid currency: {0}.".format(not_found.pop()))

    rates = {}

    for date in dates:
        url = "https://www.sbrf.ru/common/img/uploaded/banks/uploaded_mb/c_list/sdmet/download/" \
                "{2}/{1:02d}/dm{1:02d}{0:02d}.xls".format(date.day, date.month, date.year)
        try:
            xls_file = urllib2.urlopen(url, timeout = NETWORK_TIMEOUT).read()
        except urllib2.HTTPError as e:
            if e.code == 404:
                continue
            else:
                raise

        xls = xlrd.open_workbook(file_contents = xls_file)

        sheet = xls.sheets()[0]

        # Search for the title of the rate table -->
        rates_title_found = False

        for row_id in xrange(0, sheet.nrows):
            row = sheet.row(row_id)

            for cell in row:
                if (
                    cell.ctype == xlrd.XL_CELL_TEXT and
                    cell.value.find(u"Котировки продажи и покупки драгоценных металлов в обезличенном виде") >= 0
                ):
                    rates_title_found = True
                    break

            if rates_title_found:
                row_id += 1
                break
        else:
            raise Error("Unable to find the title of the rate table.")
        # Search for the title of the rate table <--

        # Search for the rate table -->
        row = sheet.row(row_id)

        texts = []
        for cell in row:
            if cell.ctype == xlrd.XL_CELL_TEXT:
                texts.append(cell.value.strip())

        if texts != [
            u"Наименование драгоценного металла",
            u"Продажа, руб. за грамм",
            u"Покупка, руб. за грамм"
        ]:
            raise Error("Unable to find the rate table.")

        row_id += 1
        # Search for the rate table <--

        # Get rates -->
        date_rates = rates.setdefault(date, {})

        for name, ru_name in (
            ("AUR_SBRF", u"Золото"),
            ("AGR_SBRF", u"Серебро"),
            ("PTR_SBRF", u"Платина"),
            ("PDR_SBRF", u"Палладий")
        ):
            row = sheet.row(row_id)

            data = []
            for cell in row:
                if cell.ctype == xlrd.XL_CELL_TEXT:
                    data.append(cell.value.strip())
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    data.append(cell.value)

            if len(data) != 3 or data[0] != ru_name:
                raise Exception("Unable to find {0}'s rate.".format(name))

            if name in currencies:
                date_rates[name] = (data[1], data[2])

            row_id += 1
        # Get rates <--

    return rates

