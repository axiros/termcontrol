"""
Tests for the `cli` module.

I.e. termcontrol being used as a wrapper for hijack on the command line
"""

print('-' * 80)
print('Do not type into the terminal when tests are running!'.upper())
print('-' * 80)

import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from tools import here, os, sp, time, wid, p, d_io, here, env, send


def test_help():
    assert os.system('termcontrol -h') == 0
    assert os.system('termcontrol --help') == 0
    assert 'positional arguments' in os.popen('termcontrol --help').read()


def test_setup_works():
    """unmodified input"""
    l = 100
    o = send(['a' * l], sw=['upper'])  # no command mode set -> no upper
    assert o['seen'].startswith('a' * l)
    assert o['seen'] == o['fifo'][0]
    assert o['app_logged'].startswith('97\n' * l)
    assert o['tc_logged'][:l] == [[97, '01000.'] for i in range(l)]


def test_cmd_upper_at_start():
    """uppercase at program start"""
    l = 100
    o = send(['a' * l], sw=['upper', 'mode'])
    # all uppercased, buffersize is >> 1 often, when automated
    assert o['seen'].startswith('A' * l)
    assert o['seen'] == o['fifo'][0]
    assert o['app_logged'].startswith('65\n' * l)
    assert o['tc_logged'][:l] == [[97, '11000.'] for i in range(l)]


def test_cmd_upper_switching_on_and_off(wait=0):
    l = 10
    # j, k is 106, 107. And i is 105
    o = send(
        ['a' * l, 'jk', 'a' * l, 'i', 'a' * 10], sw=['upper'], wait_before_send_sec=wait
    )
    # all uppercased, buffersize is >> 1 often, when automated
    # ^H is backspace, deleting the j
    v1 = 'a' * l + 'j^H' + 'A' * l + 'I' + 'a' * l
    v2 = 'a' * l + 'A' * l + 'I' + 'a' * l
    # either the j was at the end, then backspace was sent, or jk was
    # in the middle, than app sees no backspace:
    breakpoint()  # FIXME BREAKPOINT
    assert o['seen'].startswith(v1) or o['seen'].startswith(v2)
    assert o['seen'] == o['fifo'][0]
    t = o['tc_logged'][:-3]
    assert t == [
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [106, '01000.'],  # jk entered -> command mode follows:
        [107, '01000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [97, '11000.'],
        [105, '11000.'],  # exit command mode on the i
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
        [97, '01000.'],
    ]


def test_nesting():
    def nested_in_tc_subprocess():
        # we are in a subprocess of pytest now, again pytest
        d = env['TERMCONTROL_IO_DIR']
        assert env['TC_NESTED'] == d and '.outside' in d

        # first test: we want a reject on the same control dir:
        res = os.popen('termcontrol -d "%s" ls 2>&1' % d).read()
        import termcontrol as tc

        assert tc.err_same_session(d) in res

        # now we run, inside the outer tc an inner one. We want the inner to switch off
        # outer's command mode detection at start (but only if he has command mode awareness)
        # otherwise it's just an IO dubber, which won't collide:
        # I.e. this tests mode switching perfectly works, allthough nested:
        test_cmd_upper_switching_on_and_off(wait=0.1)
        # the 0.1 is a (very safe) time the pause signal being processed by the outer one
        return

    me = os.path.basename(__file__)
    if not env.get('TC_NESTED'):
        d = d_io[0] + '.outside'
        # we start a command mode aware subprocess in termcontrol - and run this testmethod again:
        cmd = (
            'export TC_NESTED="%s" && termcontrol --cmd-128 -d "$TC_NESTED" pytest -xs %s -k test_nesting'
            % (d, me)
        )
        os.makedirs(d, exist_ok=True)
        h = os.getcwd()
        os.chdir(here)
        err = os.system(cmd)
        assert not err
        return

    return nested_in_tc_subprocess()


def test_switches_understood():
    """call hijack with all kinds of combinations.
    I'll never fully understand argparse, that's why the effort:"""
    l = [
        '--cmd-mode',
        '--cmd-ctl',
        '--cmd-alt',
        '--cmd-upper',
        '--cmd-128',
        '--log',
    ]
    combis = 2 ** len(l)
    print('combinations', combis)
    for i in range(combis):
        s = str('{0:b}'.format(i)).zfill(len(l))
        print(s, i, '/', combis)
        sw = []
        for c in range(len(l) - 1, -1, -1):
            if s[c] == '1':
                sw.append(l[c])
        sw = ' '.join(sw)
        cmd = 'termcontrol %s --io-dir %s ls %s 2>&1' % (sw, d_io[0], d_io[0])
        print(cmd)
        res = os.popen(cmd).read()
        assert 'out' in res and 'in' in res
