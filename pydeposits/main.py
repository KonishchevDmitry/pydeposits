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

import getopt
import locale
import traceback

import cl.log
from cl.core import EE, Error, LogicalError

from pydeposits.rate_archive import RateArchive
import pydeposits.deposits
import pydeposits.statements


def main():
    """The application's main function."""

    debug_mode = False

    try:
        locale.setlocale(locale.LC_ALL, "")

        # Parsing command line options -->
        try:
            argv = [ string.decode(locale.getlocale()[1]) for string in sys.argv ]

            cmd_options, cmd_args = getopt.gnu_getopt(argv[1:],
                "dh", [ "debug-mode", "help" ] )

            for option, value in cmd_options:
                if option in ("-d", "--debug-mode"):
                    debug_mode = True
                elif option in ("-h", "--help"):
                    print (
                        u"""pydeposits [OPTIONS]\n\n"""
                         """Options:\n"""
                         """ -d, --debug-mode  enable debug mode\n"""
                         """ -h, --help        show this help"""
                    )
                    sys.exit(0)
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

        pydeposits.statements.print_account_statement(deposits)
    except Exception, e:
        if debug_mode:
            traceback.print_exc()
            sys.exit(1)
        else:
            sys.exit(EE(e))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

