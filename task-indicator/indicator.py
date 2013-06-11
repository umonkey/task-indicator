#!/usr/bin/env python

"""TaskWarrior active task count and duration indicator applet.
"""

__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"


import appindicator
import datetime
import dateutil.parser
import gtk
import json
import os
import subprocess
import sys
import time


FREQUENCY = 5  # seconds


class Checker(object):
    appname = "task-indicator"
    icon = "taskui"
    icon_attn = "taskui-active"

    def __init__(self):
        self.indicator = appindicator.Indicator(self.appname,
            self.icon, appindicator.CATEGORY_APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)))

        self.indicator.set_status(appindicator.STATUS_ACTIVE)
        self.indicator.set_attention_icon(self.icon_attn)
        self.menu_setup()
        self.indicator.set_menu(self.menu)

    def menu_setup(self):
        self.menu = gtk.Menu()

        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)

    def main(self):
        self.show_task()
        gtk.timeout_add(FREQUENCY * 1000, self.show_task)
        gtk.main()

    def quit(self, widget):
        sys.exit(0)

    def show_task(self):
        p = subprocess.Popen(["task", "status:pending", "start.not:", "count"],
            stdout=subprocess.PIPE)

        out = p.communicate()[0].strip()
        if not out:
            self.indicator.set_status(appindicator.STATUS_ACTIVE)
            self.indicator.set_label("Idle")
        else:
            self.indicator.set_status(appindicator.STATUS_ATTENTION)

            count = int(out)

            if str(count).endswith("1") and count != 11:
                msg = "%u active task" % count
            else:
                msg = "%u active tasks"

            if count:
                duration = self.format_duration(self.get_duration())
                msg += ", %s" % duration
            else:
                msg = "Idle"

            self.indicator.set_label(msg)

        gtk.timeout_add(FREQUENCY * 1000, self.show_task)

    def get_duration(self):
        p = subprocess.Popen(["task", "rc.json.array=1", "status:pending",
            "start.not:", "export"], stdout=subprocess.PIPE)
        out = p.communicate()[0]

        data = json.loads(out)

        now = datetime.datetime.utcnow()

        duration = datetime.timedelta()
        for task in data:
            ts = datetime.datetime.strptime(task["start"], "%Y%m%dT%H%M%SZ")
            duration += (now - ts)

        return int(duration.total_seconds())

    def format_duration(self, seconds):
        minutes = seconds / 60

        hours = minutes / 60
        minutes -= hours * 60

        return "%u:%02u" % (hours, minutes)


if __name__ == "__main__":
    Checker().main()
