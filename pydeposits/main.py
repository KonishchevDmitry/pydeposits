#!/usr/bin/env python

"""The application's startup module."""

import sys
if sys.version_info < (2, 6):
    if __name__ == "__main__":
        sys.exit("Error: pydeposits needs python >= 2.6.")
    else:
        raise Exception("pydeposits needs python >= 2.6")

import locale
locale.setlocale(locale.LC_ALL, "")
SYSTEM_ENCODING = locale.getlocale()[1]

import codecs
sys.stdout = codecs.getwriter(SYSTEM_ENCODING)(sys.stdout)
sys.stderr = codecs.getwriter(SYSTEM_ENCODING)(sys.stderr)

import os
# Setting up the module paths.
INSTALL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, INSTALL_DIR)

import datetime
import getopt
import traceback

import pycl.log
from pycl.core import EE, Error, LogicalError

from pydeposits import constants
from pydeposits.rate_archive import RateArchive
import pydeposits.deposits
import pydeposits.statements


def main():
    """The application's main function."""

    show_all = False
    debug_mode = False
    offline_mode = False
    show_expiring = None
    today = datetime.date.today()

    try:
        # Parsing command line options -->
        try:
            argv = [ string.decode(SYSTEM_ENCODING) for string in sys.argv ]

            cmd_options, cmd_args = getopt.gnu_getopt(argv[1:],
                "ade:hot:", [ "all", "debug-mode", "expiring=", "help", "offline-mode", "today=" ] )

            for option, value in cmd_options:
                if option in ("-a", "--all"):
                    show_all = True
                elif option in ("-d", "--debug-mode"):
                    debug_mode = True
                elif option in ("-e", "--expiring"):
                    try:
                        show_expiring = int(value)
                        if show_expiring < 0:
                            raise Exception("negative number")
                    except Exception, e:
                        raise Error("Invalid number of days ({0}).", value)
                elif option in ("-h", "--help"):
                    print (
                        u"""pydeposits [OPTIONS]\n\n"""
                         """Options:\n"""
                         """ -a, --all            show all deposits (not only that are not closed)\n"""
                         """ -t, --today DAY      behave like today is the day, specified by the argument in {0} format\n"""
                         """ -e, --expiring DAYS  print only deposits which will be expired in DAYS days (useful for running by cron)\n"""
                         """ -o, --offline-mode   offline mode (do not connect to the Internet for getting currency rates)\n"""
                         """ -d, --debug-mode     enable debug mode\n"""
                         """ -h, --help           show this help"""
                         .format(constants.DATE_FORMAT)
                    )
                    sys.exit(0)
                elif option in ("-o", "--offline-mode"):
                    offline_mode = True
                elif option in ("-t", "--today"):
                    try:
                        today = datetime.datetime.strptime(value, constants.DATE_FORMAT).date()
                    except Exception, e:
                        raise Error("Invalid today date ({0}).", value)
                else:
                    raise LogicalError()
            if len(cmd_args):
                raise Error("'{0}' is not recognized", cmd_args[0])
        except Exception, e:
            raise Error("Invalid arguments:").append(e)
        # Parsing command line options <--

        pycl.log.setup(debug_mode)

        if debug_mode:
            RateArchive.set_db_dir(os.path.abspath("."))
        RateArchive.enable_offline_mode(offline_mode)

        try:
            deposits = pydeposits.deposits.get()
        except Error, e:
            # To print exact error string without any modifications by EE().
            sys.exit(unicode(e))

        if show_expiring is not None:
            pydeposits.statements.print_expiring(deposits, today, show_expiring)
        else:
            pydeposits.statements.print_account_statement(deposits, today, show_all)
    except Exception, e:
        if debug_mode:
            traceback.print_exc()
            sys.exit(1)
        else:
            sys.exit("Error: " + EE(e))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

