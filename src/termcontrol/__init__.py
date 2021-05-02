"""
termcontrol package.

A terminal IO multiplexer
"""

import os, sys, pdb
import tempfile

exists = os.path.exists
env = os.environ
D_IO_PARENT = env.get('TERMCONTROL_IO_DIR', '')


def wrap_process(
    io_dir=None,
    cmd_mode=None,
    cmd_upper=None,
    cmd_signal=None,
    cmd_add_ctl=None,
    cmd_add_alt=None,
    cmd_128=None,
    logging=None,
    log_conv=None,
    rm_io_dir=False,
    **kw
):
    """
    Called from the the to-be-controlled apps at their startup phase, resulting in: 

    - A restarted process, with hijacked terminal io with in and out fifos in d_io.
    - Optionally with activated cmd_mode (uppercasing all ascii letters)

    """
    kw = dict(locals())

    if not io_dir:
        d = env.get('_tc_dir_tmp')  # helper for unspecified dirs
        if d:
            # tc called us again, we are inside
            assert env['_tc_dir_tmp'] == D_IO_PARENT, 'termcontrol env setup bogus'
            # so that the python proc can nest sth into tc again:
            del env['_tc_dir_tmp']
            return d

        io_dir = env['_tc_dir_tmp'] = tempfile.mkdtemp()

    else:
        if io_dir == D_IO_PARENT:
            # wrapped
            return io_dir

    kw.pop('kw')
    kw.pop('get', 0)
    kw['args'] = sys.argv[1:]
    kw['command'] = sys.argv[0]
    tc_cmd(**kw)
    sys.exit(err)


err_same_session = (
    lambda d: 'Already in termcontrolled session with io_dir %s. Use another IO dir.'
    % d
)


def d_io_default(create=True):
    d = '%(HOME)s/.local/share/termcontrol' % os.environ
    if not exists(d) and create:
        os.makedirs(d, exist_ok=True)
    return d


def tc_cmd(cli=False, get=False, **kw):
    here = os.path.dirname(__file__)
    if cli:
        kw.update(dict(cli._get_kwargs()))

    d = kw['io_dir']
    app = kw['command']
    if not get:
        if app == 'pause':
            # when d is given: resume another process - else ours:
            return pause(d)
        if app == 'resume':
            return resume(d)
    if not d:
        d = d_io_default(create=True)

    # nested?
    if D_IO_PARENT:
        if d == D_IO_PARENT:
            print(err_same_session(d), file=sys.stderr)
            sys.exit(1)

    if not exists(d):
        os.makedirs(d, exist_ok=True)
    is_cmd_aware = False
    cmd = [here + '/hijack']
    if not exists(cmd[0]):
        print('termcontrol: hijack not found - please compile:', hijack_cmd)
        sys.exit(1)

    if kw.get('cmd_mode'):
        cmd += ['--cmd']
    if kw.get('cmd_signal'):
        cmd += ['--cms', kw['cmd_signal']]
    if kw.get('cmd_add_ctl'):
        is_cmd_aware = True
        cmd += ['--ctl']
    if kw.get('cmd_add_alt'):
        is_cmd_aware = True
        cmd += ['--alt']
    if kw.get('cmd_upper'):
        is_cmd_aware = True
        cmd += ['--upc']
    if kw.get('cmd_128'):
        is_cmd_aware = True
        cmd += ['--128']
    if kw.get('logging'):
        cmd += ['--log']
    if kw.get('log_conv'):
        cmd += ['--lgc']
    cmd += [d]
    cmd += [app]
    cmd += kw.get('args', [])
    cmd = ' '.join(['%s' % i for i in cmd])
    if get:
        d = dict(kw)
        d['full_command'] = cmd
        return d

    if D_IO_PARENT and is_cmd_aware:
        pause(D_IO_PARENT)
    try:
        err = os.system(cmd)
        sys.exit(err)
    finally:
        if D_IO_PARENT and is_cmd_aware:
            resume(D_IO_PARENT)
        if kw.get('rm_io_dir'):
            import shutil

            try:
                shutil.rmtree(d)
            except:
                print('termcontrol could not delete IO dir', file=sys.stderr)
                pass


# check switch in handle_fifo_in_mode in hijack.c:
cmd_fifo_ctrl = 3
cmd_pause = 241
cmd_resume = 242
cmd_insert_mode = 239


pause = lambda d_io=None: send_keys(cmd_pause, d_io=d_io)
resume = lambda d_io=None: send_keys(cmd_resume, d_io=d_io)
insert_mode = lambda d_io=None: send_keys(cmd_insert_mode, d_io=d_io)


def send_keys(keys, d_io=None):
    """https://www.torsten-horn.de/techdocs/ascii.htm"""
    if d_io is not None:
        if d_io == '':
            d_io = D_IO_PARENT
    else:
        d_io = D_IO_PARENT
    if not d_io:
        return

    fn = d_io + '/in'
    if not exists(fn):
        return
    k = (keys,) if isinstance(keys, int) else keys
    k = (cmd_fifo_ctrl,) + k
    s = b''
    # with open('/tmp/agk', 'a') as fd:
    #     fd.write(str(k))
    #     fd.write('\n')

    for c in k:
        s += c.to_bytes(1, 'little')
    # this blocks if the in fifo was not cleared before but no proc active!
    with open(fn, 'wb', 0) as fd:
        fd.write(s)


def breakpointx():
    insert_mode()
    import threading, time

    def send_s():
        # time.sleep(0.1)
        send_keys(b'\53\x0d')

    # threading.Thread(target=lambda: send_s).start()
    send_s()
    pdb.set_trace()
