# -*- coding: utf-8 -*-

"""Contains tools for getting rate info from Sberbank."""

import datetime
import logging
import re
import urllib.request

from decimal import Decimal

import xlrd

from pydeposits import constants
from pydeposits.util import Error

LOG = logging.getLogger("pydeposits.sbrf")


# TODO: get all rates per day
def get_rates(dates):
    """Returns Sberbank's rates for a specified dates."""

    rates = {}

    rate_urls = {}
    url_prefix = "http://sberbank.ru/"
    rate_list_re = re.compile(r"""<ul\s+class\s*=\s*["']docs["']\s*>(.*?)</ul>""",
        re.IGNORECASE | re.MULTILINE | re.DOTALL)
    rate_url_re = re.compile(r"""
        <li\s+class\s*=\s*["']xls["']>\s*
            <a\s+href\s*=\s*["'](
                # URLs may be:
                # /common/img/uploaded/c_list/sdmet/download/2010/01/dm0115.xls"
                # /common/img/uploaded/banks/uploaded_mb/c_list/sdmet/download/2011/03/dm0310.xls"
                # /common/img/uploaded/banks/uploaded_mb/c_list/sdmet/download/2011/03/dm0310_2.xls"
                [^"']+/c_list/sdmet/download/(\d{4})/(\d{2})/dm(\d{2})(\d{2})(_\d)?.xls
            )["']
    """, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

    for date in dates:
        try:
            # SBRF has rate info for metals only since 05.03.2003
            if date < datetime.date(2003, 3, 5):
                continue

            LOG.info("Getting SBRF's currency rates for %s...", date)

            # Getting rates for the month -->
            month_spec = (date.year, date.month)

            day_urls = rate_urls.get(month_spec)
            if day_urls is None:
                day_urls = {}

                url = "{0}moscow/ru/valkprev/archive_1/index.php?year114={1}&month114={2}".format(
                    url_prefix, date.year, date.month)

                rate_list_html = urllib.request.urlopen(
                    url, timeout = constants.NETWORK_TIMEOUT).read().decode("cp1251")

                match = rate_list_re.search(rate_list_html)
                if not match:
                    raise Error("server returned unknown HTML response")
                rate_list_html = match.group(1)

                matches = rate_url_re.findall(rate_list_html)
                if not matches:
                    # Month may be empty if it's only starting and there are
                    # some holidays in the first days.
                    if (
                        datetime.date.today().month == date.month and (
                            (date - datetime.date(date.year, date.month, 1)).days <= 2 or

                            # Long New Year holidays
                            date.month == 1 and (date - datetime.date(date.year, date.month, 1)).days <= 10 or

                            # Long holidays in May
                            date.month == 5 and (date - datetime.date(date.year, date.month, 1)).days <= 6
                        )
                    ):
                        continue
                    else:
                        raise Error("server returned unknown HTML response")

                for match in matches:
                    if date.year == int(match[1]) and date.month == int(match[2]):
                        url = match[0]
                        if "://" not in url:
                            url = url_prefix + url.lstrip("/")

                        day_urls.setdefault(int(match[4]), []).append(url)
                    else:
                        # If we ask for data that SBRF doesn't have, it returns data for previous month/year.
                        pass

                rate_urls[month_spec] = day_urls
            # Getting rates for the month <--

            # Getting XML file with rates for the date -->
            if date.day not in day_urls:
                LOG.debug("There is no data for SBRF's currency rates for %s...", date)
                continue

            for url in day_urls[date.day]:
                try:
                    xls_contents = urllib.request.urlopen(
                        url, timeout = constants.NETWORK_TIMEOUT).read()
                except urllib.request.HTTPError as e:
                    if e.code == 404:
                        # It's a common error when we have 2 reports per day
                        LOG.debug("Unable to download '%s': %s.", url, e)
                    else:
                        raise e
                else:
                    break
            else:
                raise e
            # Getting XML file with rates for the date <--

            try:
                xls = xlrd.open_workbook(file_contents = xls_contents)
            except Exception as e:
                LOG.error("Unable to read data for SBRF's currency rates for %s: %s.", date, e)
                continue

            # The *.xls file can contain a few empty sheets.
            # Choosing a non-empty sheet.
            # -->
            sheet_id = -1

            for id, sheet in enumerate(xls.sheets()):
                empty = True

                for row_id in range(0, sheet.nrows):
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

            for row_id in range(0, sheet.nrows):
                row = sheet.row(row_id)

                for cell in row:
                    if (
                        cell.ctype == xlrd.XL_CELL_TEXT and
                        (
                            cell.value.find("Котировки покупки-продажи драгоценных металлов в обезличенном виде") >= 0
                            or
                            cell.value.find("Котировки продажи и покупки драгоценных металлов в обезличенном виде") >= 0
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
                "Наименование драгоценного металла",
                "Продажа, руб. за грамм",
                "Покупка, руб. за грамм"
            ]:
                raise Error("Unable to find the rate table.")

            row_id += 1
            # Search for the rate table <--

            # Get rates -->
            date_rates = rates.setdefault(date, {})

            for name, ru_name in (
                ("AUR_SBRF", "Золото"),
                ("AGR_SBRF", "Серебро"),
                ("PTR_SBRF", "Платина"),
                ("PDR_SBRF", "Палладий")
            ):
                row = sheet.row(row_id)

                data = []
                for cell in row:
                    if cell.ctype == xlrd.XL_CELL_TEXT:
                        data.append(cell.value.strip())
                    elif cell.ctype == xlrd.XL_CELL_NUMBER:
                        data.append(cell.value)

                if len(data) != 3 or data[0] != ru_name:
                    raise Error("Unable to find {}'s rate.", name)

                date_rates[name] = ( Decimal(str(data[1])), Decimal(str(data[2])) )

                row_id += 1
                if row_id >= sheet.nrows:
                    break
            # Get rates <--

            LOG.debug("Gotten rates: %s", date_rates)
        except Exception as e:
            raise Error("Unable to get rate info from Sberbank for {}:", date).append(e)

    return rates
