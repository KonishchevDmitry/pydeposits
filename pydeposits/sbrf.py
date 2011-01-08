# -*- coding: utf-8 -*-

"""Contains tools for getting rate info from Sberbank."""

from decimal import Decimal
import datetime
import logging
import urllib2

import xlrd

from cl.core import Error
from pydeposits import constants

LOG = logging.getLogger("pydeposits.sbrf")


# TODO: get all rates per day
def get_rates(dates):
    """Returns Sberbank's rates for a specified dates."""

    rates = {}

    for date in dates:
        try:
            # SBRF has rate info for metals only since 05.03.2003
            if date < datetime.date(2003, 3, 5):
                continue

            LOG.info("Getting SBRF's currency rates for %s...", date)

            if date < datetime.date(2010, 2, 1):
                url_prefix = "https://www.sbrf.ru/common/img/uploaded/c_list/sdmet/download"
            else:
                url_prefix = "https://www.sbrf.ru/common/img/uploaded/banks/uploaded_mb/c_list/sdmet/download"
            url = "{0}/{3}/{2:02d}/dm{2:02d}{1:02d}.xls".format(url_prefix, date.day, date.month, date.year)

            try:
                xls_contents = urllib2.urlopen(url, timeout = constants.NETWORK_TIMEOUT).read()
            except urllib2.HTTPError as e:
                if e.code == 404:
                    LOG.debug("There is no data for SBRF's currency rates for %s...", date)
                    continue
                else:
                    raise

            xls = xlrd.open_workbook(file_contents = xls_contents)

            # The *.xls file can contain a few empty sheets.
            # Choosing a non-empty sheet.
            # -->
            sheet_id = -1

            for id, sheet in enumerate(xls.sheets()):
                empty = True

                for row_id in xrange(0, sheet.nrows):
                    for cell in sheet.row(row_id):
                        if cell.ctype == xlrd.XL_CELL_TEXT and cell.value.strip():
                            empty = False
                            break

                    if not empty:
                        break

                if not empty:
                    if sheet_id >= 0:
                        raise Error("the *.xls file contains more than one sheet")
                    else:
                        sheet_id = id

            if sheet_id < 0:
                raise Error("the *.xls file doesn't contain any non-empty sheet")
            # <--

            sheet = xls.sheets()[sheet_id]

            # Search for the title of the rate table -->
            rates_title_found = False

            for row_id in xrange(0, sheet.nrows):
                row = sheet.row(row_id)

                for cell in row:
                    if (
                        cell.ctype == xlrd.XL_CELL_TEXT and
                        (
                            cell.value.find(u"Котировки покупки-продажи драгоценных металлов в обезличенном виде") >= 0
                            or
                            cell.value.find(u"Котировки продажи и покупки драгоценных металлов в обезличенном виде") >= 0
                        )
                    ):
                        rates_title_found = True
                        break

                if rates_title_found:
                    row_id += 1
                    break
            else:
                raise Error("Unable to find the title of the rate table.")
            # Search for the title of the rate table <--

            if row_id + 1 >= sheet.nrows:
                raise Error("The rate table is truncated.")

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
                    raise Error("Unable to find {0}'s rate.", name)

                date_rates[name] = ( Decimal(str(data[1])), Decimal(str(data[2])) )

                row_id += 1
                if row_id >= sheet.nrows:
                    break
            # Get rates <--

            LOG.debug("Gotten rates: %s", date_rates)
        except Exception as e:
            raise Error("Unable to get rate info from Sberbank for {0}:", date).append(e)

    return rates

