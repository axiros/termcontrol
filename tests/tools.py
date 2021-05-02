"""Testing tools for termcontrol wrapped processes.

requires stdin available, i.e. pytest -s

"""

import os
import subprocess as sp
import tempfile
import time
from threading import Thread
import json


def p(o):
    try:
        o = dict(o)
    except:
        o = list(o)
    print(json.dumps(dict(o), indent=8, default=str, sort_keys=True))


# changeable:
d_io = [tempfile.mkdtemp()]
here = os.path.dirname(__file__)
input_logger = here + '/input_logger.py'
termcontrol_log = '%(HOME)s/termcontrol_input.log' % os.environ
wid = os.environ['WINDOWID']
out_fifo = []
input_logger_exit_key = 97
env = os.environ


def readfile(fn):
    with open(fn) as fd:
        return fd.read()


def xdo(mode, seq):
    os.system('xdotool %s --window %s "%s"' % (mode, wid, seq))


def xtype(in_sequences, wait_flag, stop_key):
    def t(in_sequences=in_sequences, wait_flag=wait_flag, stop_key=stop_key):
        while not os.path.exists(wait_flag):
            time.sleep(0.01)
        fifo = open(d_io[0] + '/out')
        # Thread(target=read_fifo, daemon=True).start()

        print('start')
        for seq in in_sequences:
            if seq.startswith('key:'):
                xdo('key', seq.split('key:', 1)[1])
            else:
                xdo('type', seq)
        # this causes our currently blocking (os.popen.read) main thread to unblock,
        # since input logger exits now (reads EOF):
        xdo('key', 'Return')
        xdo('type', chr(stop_key))
        xdo('key', 'Return')
        out_fifo.append(fifo.read())
        fifo.close()

    Thread(target=t, daemon=True).start()


def tc_logged():
    r = []
    tc = readfile(termcontrol_log).splitlines()
    while tc:
        l = tc.pop(0).split()
        k = 2
        while k < len(l):
            r.append([int(l[k]), l[1]])
            k += 2
    return r


def send(in_sequences, sw=[], stop_key=125, wait_before_send_sec=0):
    """Sending stuff into the process - and returning in_sequences it saw, logged and also
    in_sequences termcontrol wrote on the out fifo
    """
    out_fifo.clear()
    fn_in = d_io[0] + '/input.log'
    fn_is_listening = d_io[0] + '/input_logger_is_listening.flag'
    for f in fn_in, termcontrol_log, fn_is_listening:
        if os.path.exists(f):
            os.unlink(f)
    # build command line:
    a = 'termcontrol --log --io-dir "%s" ' % d_io[0]
    a += ' '.join(['--cmd-' + i for i in sw])
    env['import_switches'] = ''
    if env.get('import_mode'):
        # here the test logger will wrap itself, with the given switches:
        env['import_switches'] = a.split(' ', 1)[1]
        a = ''
    a += (
        ' python -u '
        + input_logger
        + ' "%s" "%s" %s' % (fn_in, fn_is_listening, stop_key)
    )

    #
    l = in_sequences
    # when tc needs to suspend the parent process we need a little time before going live:
    time.sleep(wait_before_send_sec)
    xtype(l if isinstance(l, list) else [l], fn_is_listening, stop_key)
    t0 = time.time()
    seen = os.popen(a).read()
    while not out_fifo:
        time.sleep(0.01)
        if time.time() - t0 > 2:
            raise Exception(
                'os.popen error running. You need to run me with -s in pytest! %s' % a
            )

    return {
        'seen': seen,
        'app_logged': readfile(fn_in),
        'fifo': out_fifo,
        'tc_logged': tc_logged(),
    }
