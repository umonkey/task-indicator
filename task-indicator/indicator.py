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


FREQUENCY = 1  # seconds


def run_command(command):
    print >> sys.stderr, "> %s" % " ".join(command)
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    return p.communicate()[0]


def get_task_info(uuid):
    out = run_command(["task", uuid, "export"])
    return json.loads(out)


class TaskWarrior(object):
    def __init__(self):
        self.filename = self.get_filename()
        self.mtime = None
        self.tasks = None

    def poll(self):
        """Returns True if the file was updated since last check."""
        mtime = os.stat(self.filename).st_mtime
        if mtime != self.mtime:
            print "Task database changed."
            self.tasks = None
            self.mtime = mtime
            return True
        return False

    def get_filename(self):
        for line in run_command(["task", "_show"]).split("\n"):
            if line.startswith("data.location="):
                folder = line.split("=", 1)[1].strip()
                return os.path.join(folder, "pending.data")

    def get_tasks(self):
        if self.tasks is None:
            print "Reloading tasks."
            self.tasks = self.load_tasks()
        return self.tasks

    def load_tasks(self):
        f = self.get_task_filter()
        output = run_command(["task", "rc.json.array=1"] + f + ["export"])
        return json.loads(output)

    def get_task_filter(self):
        config = os.path.expanduser("~/.taskui-filter")
        if not os.path.exists(config):
            return ["status:pending", "or", "start.not:"]
        with open(config, "rb") as f:
            return shlex.split(f.read().strip())


class Dialog(gtk.Window):
    def __init__(self):
        super(Dialog, self).__init__()

        self.task = None
        self.callback = None

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
            self.open_web_pages()

        run_command(["task", self.task["uuid"], action])
        self.hide()

        if self.callback:
            self.callback()

    def open_web_pages(self):
        for word in self.task["description"].split(" "):
            if "://" in word:
                run_command(["xdg-open", word])

    def show_task(self, task, callback):
        self.task = get_task_info(task["uuid"])
        self.callback = callback

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
        self.tw = TaskWarrior()

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

    def menu_add_tasks(self):
        print "Updating menu contents."

        for item in self.menu.get_children():
            if item.get_data("is_dynamic"):
                self.menu.remove(item)
        self.task_items = []

        data = self.tw.get_tasks()

        for task in sorted(data, key=self.task_sort):
            item = gtk.CheckMenuItem(self.format_menu_label(task), use_underline=False)
            if task.get("start"):
                item.set_active(True)
            item.connect("activate", self.on_task_toggle)
            item.set_data("task", task)
            item.set_data("is_dynamic", True)
            item.show()

            self.menu.insert(item, len(self.task_items))
            self.task_items.append(item)

        if data:
            item = gtk.SeparatorMenuItem()
            item.set_data("is_dynamic", True)
            item.show()
            self.menu.insert(item, len(self.task_items))
            self.task_items.append(item)

    def format_menu_label(self, task):
        proj = task["project"].split(".")[-1]

        desc = task["description"]
        if desc.startswith("(bw)"):
            desc = desc.split(" ", 2)[-1]

        title = u"%s:\t%s" % (proj, desc)
        return title

    def task_sort(self, task):
        return task["project"], self.format_menu_label(task)

    def on_task_toggle(self, widget):
        task = widget.get_data("task")

        self.dialog.show_task(task, callback=self.update_status)
        return

        if widget.get_active():
            run_command(["task", task["uuid"], "start"])
            # Open URLs from the task description
            for word in task["description"].split(" "):
                if "://" in word:
                    run_command(["xdg-open", word])
        else:
            run_command(["task", task["uuid"], "stop"])
        self.update_status()

    def main(self):
        """Enters the main program loop"""
        self.on_timer()

    def stop(self, widget):
        """Stops running tasks"""
        for task in self.get_running_tasks():
            run_command(["task", task["uuid"], "stop"])
        self.stop_item.hide()
        self.update_status()

    def quit(self, widget):
        """Ends the applet"""
        sys.exit(0)

    def on_timer(self):
        """Timer handler which updates the list of tasks and the status."""
        gtk.timeout_add(FREQUENCY * 1000, self.on_timer)

        if self.tw.poll():
            self.menu_add_tasks()

        self.update_status()  # display current duration, etc

    def update_status(self):
        """Changes the indicator icon and text label according to running
        tasks."""
        tasks = [t for t in self.tw.get_tasks() if "start" in t]

        if not tasks:
            self.indicator.set_label("Idle")
            self.indicator.set_status(appindicator.STATUS_ACTIVE)
            self.stop_item.hide()
        else:
            self.indicator.set_status(appindicator.STATUS_ATTENTION)
            self.stop_item.show()

            msg = "%u/%s" % (len(tasks),
                self.format_duration(self.get_duration()))

            self.indicator.set_label(msg)

    def get_duration(self):
        now = datetime.datetime.utcnow()

        duration = datetime.timedelta()
        for task in self.tw.get_tasks():
            if "start" in task:
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
