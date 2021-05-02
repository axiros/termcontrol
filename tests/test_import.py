"""Tests for the `cli` module."""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from tools import os, sp, time, p, d_io, here, send

import test_cli
import termcontrol


def test_imp_setup_works():
    os.environ['import_mode'] = 'true'
    test_cli.test_setup_works()


def test_imp_cmd_upper_at_start():
    os.environ['import_mode'] = 'true'
    test_cli.test_cmd_upper_at_start()


def test_imp_cmd_upper_switching_on_and_off():
    os.environ['import_mode'] = 'true'
    test_cli.test_cmd_upper_switching_on_and_off()
