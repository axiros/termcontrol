#!/usr/bin/env python
import sys
import os
from json import loads

# This test program can work wrapped from outside (when runnint test_cli) but also
# it wraps itself, like python processes, when this env var is present:
# This way we can reuse all cli tests, also for the import tests:
import_switches = args = os.environ.pop('import_switches', '')
if args:
    # we are the test utility for the python import tests. this contains the params:
    import termcontrol

    # we make use of the cli's get command, which spits out, amongst aother all params:
    from termcontrol import cli

    i = 'x ' + args + ' --get'
    i = i.replace('"', '').replace("'", '')  # this is testmode. dirs are sane
    args_kw = cli.main(i.split(' '))
    args_kw.pop('get_cmd')
    args_kw.pop('args', 0)
    args_kw.pop('command', 0)
    args_kw.pop('full_command')

    # we feed the params into our python api:
    # process will now restart itself, wrapped:
    d_io = termcontrol.wrap_process(**args_kw)


# on presence of this file, the test programm will start sending stuff into us

wait_flag = None
# on presence of this input character we will exit:
stop_key = 125


def main():
    if wait_flag:
        with open(wait_flag, 'w') as fd:
            fd.write('ready')

    while True:
        c = sys.stdin.buffer.read(1)
        # print(ord(c))
        if not c or ord(c) == stop_key:
            break
        # sys.stdout.buffer.write(c)
        c = ord(c)
        with open(logfile, 'a') as fd:
            fd.write('%s\n' % c)
            fd.flush()


if __name__ == '__main__':
    logfile = sys.argv[1] if len(sys.argv) > 1 else 'logged_input'
    if len(sys.argv) > 2:
        wait_flag = sys.argv[2]
    if len(sys.argv) > 3:
        stop_key = int(sys.argv[3])

    main()
