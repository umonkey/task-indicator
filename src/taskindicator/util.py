# encoding=utf-8

from __future__ import print_function

import calendar
import datetime
import json
import subprocess
import sys

import pygtk
pygtk.require("2.0")
import gtk


def log(msg, *args):
    if args:
        msg = msg.format(*args)
    print(msg, file=sys.stderr)


def run_command(command, fail=True):
    log("> {0}", " ".join(command))
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    out = p.communicate()[0]
    if p.returncode and fail:
        raise RuntimeError("Command failed with code %s." % p.returncode)
    return out


def strip_description(text):
    words = text.split(" ")

    if text.startswith("(bw)"):
        words = words[2:-2]

    # Strip shortened urls (used by bugwarrior, etc).
    if len(words) > 1 and "://" in words[-1]:
        del words[-1]
        if words[-1] == "..":
            del words[-1]

    return " ".join(words).strip()


def get_icon_path(icon_name):
    theme = gtk.icon_theme_get_default()

    icon = theme.lookup_icon(icon_name, 0, 0)
    if icon:
        log("Found icon {0}: {1}", icon_name, icon.get_filename())
        return icon.get_filename()

    log("No icon named {0}", icon_name)


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


def now():
    return datetime.datetime.now(UTC())
