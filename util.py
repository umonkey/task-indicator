# encoding=utf-8

import json
import subprocess
import sys


def run_command(command):
    print >> sys.stderr, "> %s" % " ".join(command)
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    return p.communicate()[0]


def find_tasks(args):
    command = ["task", "rc.json.array=1"] + args + ["export"]
    return json.loads(run_command(command))


def strip_description(text):
    if text.startswith("(bw)"):
        words = text.split(" ")
        text = " ".join(words[2:-2])
    return text
