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
import shlex
import subprocess
import sys
import time


FREQUENCY = 5  # seconds


def get_task_info(uuid):
    p = subprocess.Popen(["task", uuid, "export"],
        stdout=subprocess.PIPE)
    out = p.communicate()[0]
    return json.loads(out)


class Dialog(gtk.Window):
    def __init__(self):
        super(Dialog, self).__init__()

        self.task = None

        self.set_size_request(250, 100)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title("Task properties")

        self.entry = gtk.Entry()
        self.btn_start = gtk.Button("Start")
        self.btn_start.connect("clicked", self.on_start)

        self.btn_cancel = gtk.Button("Cancel")
        self.btn_cancel.connect("clicked", self.on_cancel)

        self.vbox = gtk.VBox(spacing=8)
        self.vbox.pack_start(self.entry)

        self.hbox = gtk.HBox(spacing=8)
        self.hbox.pack_start(self.btn_start)
        self.hbox.pack_start(self.btn_cancel)
        self.vbox.pack_start(self.hbox)

        self.add(self.vbox)

    def on_cancel(self, widget):
        self.hide()

    def on_start(self, widget):
        if self.task.get("start"):
            action = "stop"
        else:
            action = "start"

        p = subprocess.Popen(["task", self.task["uuid"], action])
        p.wait()
        self.hide()

    def show_task(self, task):
        self.task = get_task_info(task["uuid"])
        self.entry.set_text(task["description"])
        if self.task.get("start"):
            self.btn_start.set_label("Stop")
        else:
            self.btn_start.set_label("Start")
        self.show_all()


class Checker(object):
    """The indicator applet.  Displays the TaskWarrior icon and current
    activity time, if any.  The pop-up menu can be used to start or stop
    running tasks.
    """
    appname = "task-indicator"
    icon = "taskui"
    icon_attn = "taskui-active"

    def __init__(self):
        self.task_items = []

        self.indicator = appindicator.Indicator(self.appname,
            self.icon, appindicator.CATEGORY_APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)))

        self.indicator.set_status(appindicator.STATUS_ACTIVE)
        self.indicator.set_attention_icon(self.icon_attn)
        self.menu_setup()
        self.indicator.set_menu(self.menu)

        self.dialog = Dialog()

    def menu_setup(self):
        self.menu = gtk.Menu()

        self.stop_item = gtk.MenuItem("Stop all")
        self.stop_item.connect("activate", self.stop)
        self.stop_item.show()
        self.menu.append(self.stop_item)

        self.quit_item = gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)

        self.menu_add_tasks()

    def menu_add_tasks(self):
        data = self.get_all_tasks()

        for task in sorted(data, key=self.task_sort):
            title = u"%s:\t%s" % (task["project"].split(".")[-1], task["description"])
            item = gtk.CheckMenuItem(title, use_underline=False)
            if task.get("start"):
                item.set_active(True)
            item.connect("activate", self.on_task_toggle)
            item.set_data("task", task)
            item.show()
            self.menu.insert(item, len(self.task_items))
            self.task_items.append(item)

        if data:
            item = gtk.SeparatorMenuItem()
            item.show()
            self.menu.insert(item, len(self.task_items))
            self.task_items.append(item)

    def task_sort(self, task):
        return task["project"], -float(task["urgency"]), task["description"]

    def on_task_toggle(self, widget):
        task = widget.get_data("task")

        self.dialog.show_task(task)
        return

        if widget.get_active():
            subprocess.Popen(["task", task["uuid"], "start"]).wait()
            # Open URLs from the task description
            for word in task["description"].split(" "):
                if "://" in word:
                    subprocess.Popen(["xdg-open", word])
        else:
            subprocess.Popen(["task", task["uuid"], "stop"]).wait()
        self.update_status()

    def main(self):
        """Enters the main program loop"""
        self.update_status()
        gtk.timeout_add(FREQUENCY * 1000, self.update_status)

    def stop(self, widget):
        """Stops running tasks"""
        for task in self.get_running_tasks():
            subprocess.Popen(["task", task["uuid"], "stop"]).wait()
        self.stop_item.hide()
        self.update_status()

    def quit(self, widget):
        """Ends the applet"""
        sys.exit(0)

    def update_status(self):
        p = subprocess.Popen(["task", "status:pending", "start.not:", "count"],
            stdout=subprocess.PIPE)

        out = p.communicate()[0].strip()
        count = int(out.strip())

        if not count:
            self.indicator.set_label("Idle")
            self.indicator.set_status(appindicator.STATUS_ACTIVE)
            self.stop_item.hide()
        else:
            self.indicator.set_status(appindicator.STATUS_ATTENTION)
            self.stop_item.show()

            if str(count).endswith("1") and count != 11:
                msg = "%u active task" % count
            else:
                msg = "%u active tasks" % count

            if count:
                duration = self.format_duration(self.get_duration())
                msg += ", %s" % duration
            else:
                msg = "Idle"

            self.indicator.set_label(msg)

        gtk.timeout_add(FREQUENCY * 1000, self.update_status)

    def get_running_tasks(self):
        return self.get_filtered_tasks(["status:pending", "start.not:"])

    def get_all_tasks(self):
        return self.get_filtered_tasks(self.get_task_filter())

    def get_filtered_tasks(self, filter):
        cmd = ["task", "rc.json.array=1"] + filter + ["export"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        return json.loads(stdout)

    def get_task_filter(self):
        config = os.path.expanduser("~/.taskui-filter")
        if not os.path.exists(config):
            return ["status:pending", "project:work"]
        with open(config, "rb") as f:
            return shlex.split(f.read().strip())

    def get_duration(self):
        data = self.get_running_tasks()
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
    gtk.main()
