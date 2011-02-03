#!/usr/bin/env python

"""The application's startup module."""

import sys

if sys.version_info < (2, 6):
    if __name__ == "__main__":
        sys.exit("Error: pydeposits needs python >= 2.6.")
    else:
        raise Exception("pydeposits needs python >= 2.6")

import os

# Setting up the module paths.
INSTALL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, INSTALL_DIR)

import datetime
import getopt
import locale
import traceback

import cl.log
from cl.core import EE, Error, LogicalError

from pydeposits import constants
from pydeposits.rate_archive import RateArchive
import pydeposits.deposits
import pydeposits.statements


def main():
    """The application's main function."""

    show_all = False
    debug_mode = False
    today = datetime.date.today()

    try:
        locale.setlocale(locale.LC_ALL, "")

        # Parsing command line options -->
        try:
            argv = [ string.decode(locale.getlocale()[1]) for string in sys.argv ]

            cmd_options, cmd_args = getopt.gnu_getopt(argv[1:],
                "adht:", [ "all", "debug-mode", "help", "today=" ] )

            for option, value in cmd_options:
                if option in ("-a", "--all"):
                    show_all = True
                elif option in ("-d", "--debug-mode"):
                    debug_mode = True
                elif option in ("-h", "--help"):
                    print (
                        u"""pydeposits [OPTIONS]\n\n"""
                         """Options:\n"""
                         """ -a, --all         show all deposits (not only that are not closed)\n"""
                         """ -t, --today       behave like today is the day specified by the argument in {0} format\n"""
                         """ -d, --debug-mode  enable debug mode\n"""
                         """ -h, --help        show this help"""
                         .format(constants.DATE_FORMAT)
                    )
                    sys.exit(0)
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

        cl.log.setup(debug_mode)

        if debug_mode:
            RateArchive.set_db_dir(os.path.abspath("."))

        try:
            deposits = pydeposits.deposits.get()
        except Error, e:
            # To print exact error string without any modifications by EE().
            sys.exit(unicode(e))

        pydeposits.statements.print_account_statement(deposits, today, show_all)
    except Exception, e:
        if debug_mode:
            traceback.print_exc()
            sys.exit(1)
        else:
            sys.exit("pydeposits crashed: " + EE(e))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

