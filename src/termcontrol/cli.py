#!/usr/bin/env python
import os, sys
import argparse
import subprocess

import termcontrol

d_dflt = termcontrol.d_io_default(create=False)


def main(args=None):
    """
    Run the main program.

    This function is executed when you type `termcontrol` or `python -m termcontrol`.

    Arguments:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    args = args if args is not None else sys.argv
    args = args[1:]
    args.append('')
    parser = argparse.ArgumentParser(
        prog='termcontrol',
        epilog='The given command will be run within a process with hijacked terminal I/O',
    )

    parser.add_argument(
        '-C',
        '--cmd-mode',
        action='store_true',
        dest='cmd_mode',
        help='Start controlled process with command mode activated (all letters uppercased). Hit i to enter insert mode, jk to go back to command mode.',
    )
    parser.add_argument(
        '-S',
        '--cmd-signal',
        dest='cmd_signal',
        type=int,
        default=0,
        help='Send an alt+<this code> to the app, so that it knows you switched to command mode. Eg. -S 97 => send alt+a',
    )
    parser.add_argument(
        '-I',
        '--insert-mode',
        dest='ins_mode',
        default='i',
        help='Which key for insert mode (code or char)',
    )
    parser.add_argument(
        '-c',
        '--cmd-ctl',
        action='store_true',
        dest='cmd_add_ctl',
        help='In command mode, prefix all LETTER keys with control key (a->ctrl+a, A-ctrl+a)',
    )
    parser.add_argument(
        '-a',
        '--cmd-alt',
        action='store_true',
        dest='cmd_add_alt',
        help='In command mode, prefix ALL keys with alt key (a->alt+a, A->alt+A, !->alt+!)',
    )
    parser.add_argument(
        '-u',
        '--cmd-upper',
        action='store_true',
        dest='cmd_upper',
        help='In command mode, turn all lowercase LETTER keys into uppercase (a->A)',
    )
    parser.add_argument(
        '-8',
        '--cmd-128',
        action='store_true',
        dest='cmd_128',
        help='In command mode, add 128 to all keys',
    )
    parser.add_argument(
        '-l',
        '--log',
        action='store_true',
        dest='log',
        help='Log stdin keys as typed by user numerically to $HOME/termcontrol_input.log',
    )
    parser.add_argument(
        '-L',
        '--log-conv',
        action='store_true',
        dest='log_conv',
        help='Log stdin keys as sent to app (in command mode) numerically to $HOME/termcontrol_input.log',
    )

    parser.add_argument(
        '-d',
        '--io-dir',
        dest='io_dir',
        default='',
        help='Directory where I/O fifos will be created (default: %s)' % d_dflt,
    )
    parser.add_argument(
        '-g',
        '--get-cmd',
        dest='get_cmd',
        action='store_true',
        help='Print and return command - do not run it.',
    )
    parser.add_argument(
        '-R',
        '--rm-io-dir',
        action='store_false',
        default=False,
        dest='rm_io_dir',
        help='Remove the IO directory after run.',
    )

    parser.add_argument(
        dest='command', help='The application to start (default: sh)',
    )
    parser.add_argument(
        'args',
        nargs=argparse.REMAINDER,
        help='The application to start (default: sh). Understood: pause and resume, only controlling an outer tc process.',
    )

    p: argparse.Namespace = parser.parse_args(args)
    if p.command == '':
        p.command = '/bin/sh'

    cmd = termcontrol.tc_run(cli=p, get=p.get_cmd)
    if p.get_cmd:
        return cmd


if __name__ == '__main__':
    main()
