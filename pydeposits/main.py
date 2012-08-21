"""The application's startup module."""

from __future__ import unicode_literals

import datetime
import getopt
import os
import sys
import traceback

import pycl.log
import pycl.main
import pycl.misc
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

    pycl.main.setup_environment()

    try:
        # Parsing command line options -->
        try:
            argv = [ pycl.misc.to_unicode(arg) for arg in sys.argv ]

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
                        """pydeposits [OPTIONS]\n\n"""
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
