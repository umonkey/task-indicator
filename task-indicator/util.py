# encoding=utf-8

import subprocess
import sys


def run_command(command):
    print >> sys.stderr, "> %s" % " ".join(command)
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    return p.communicate()[0]
