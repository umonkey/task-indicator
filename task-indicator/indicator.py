#!/usr/bin/env python

"""TaskWarrior active task count and duration indicator applet.
"""

__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"


import appindicator
import datetime
import dateutil.parser
import gtk
import os
import sys
import time

import database
import properties
import search
from util import run_command


FREQUENCY = 1  # seconds


def get_task_info(uuid):
    out = run_command(["task", uuid, "export"])
    return json.loads(out)


class Checker(object):
    """The indicator applet.  Displays the TaskWarrior icon and current
    activity time, if any.  The pop-up menu can be used to start or stop
    running tasks.
    """
    appname = "task-indicator"
    icon = "taskui"
    icon_attn = "taskui-active"

    def __init__(self):
        self.toggle_lock = False

        self.task_items = []
        self.database = database.Database(callback=self.on_tasks_changed)

        self.indicator = appindicator.Indicator(self.appname,
            self.icon, appindicator.CATEGORY_APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)))

        self.indicator.set_status(appindicator.STATUS_ACTIVE)
        self.indicator.set_attention_icon(self.icon_attn)

        self.menu_setup()
        self.indicator.set_menu(self.menu)

        self.dialog = properties.Dialog(callback=self.on_task_info_closed)
        self.dialog.on_task_start = self.on_start_task
        self.dialog.on_task_stop = self.on_stop_task

        self.search_dialog = search.Dialog()
        self.search_dialog.on_activate_task = self.on_search_callback

        self.database.start_polling()

    def on_start_task(self, task):
        run_command(["task", task["uuid"], "start"])
        self.update_status()
        self.open_task_webpage(task)

    def on_stop_task(self, task):
        run_command(["task", task["uuid"], "stop"])
        self.update_status()

    def open_task_webpage(self, task):
        for word in task["description"].split(" "):
            if "://" in word:
                run_command(["xdg-open", word])

    def menu_setup(self):
        self.menu = gtk.Menu()

        self.show_all_item = gtk.MenuItem("Show more...")
        self.show_all_item.connect("activate", self.on_show_all_tasks)
        self.show_all_item.show()
        self.menu.append(self.show_all_item)

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

        data = self.database.get_tasks()

        for task in sorted(data, key=self.task_sort)[:10]:
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
        """Returns the data to sort tasks by."""
        # print task["urgency"], task["description"]
        is_running = "start" in task
        return -is_running, -float(task["urgency"])

    def on_show_all_tasks(self, widget):
        self.search_dialog.show_all()

    def on_search_callback(self, uuid):
        tasks = [t for t in self.database.get_tasks() if t["uuid"] == uuid]
        if not tasks:
            print "Oops, task %s does not exist." % uuid
        else:
            self.dialog.show_task(tasks[0])

    def on_task_toggle(self, widget):
        if self.toggle_lock:
            return

        self.toggle_lock = True
        widget.set_active(not widget.get_active())

        task = widget.get_data("task")
        self.dialog.show_task(task)
        self.toggle_lock = False
        return True

    def on_task_info_closed(self, updates):
        """Updates the task when the task info window is closed.  Updates
        is a dictionary with 'uuid' and modified fields."""
        uuid = updates["uuid"]
        del updates["uuid"]

        if updates:
            command = ["task", uuid, "mod"]
            for k, v in updates.items():
                command.append("%s:%s" % (k, v))
            run_command(command)

        self.update_status()

    def main(self):
        """Enters the main program loop"""
        self.on_timer()

    def stop(self, widget):
        """Stops running tasks"""
        for task in self.database.get_tasks():
            if "start" in task:
                run_command(["task", task["uuid"], "stop"])
        self.stop_item.hide()
        self.update_status()

    def quit(self, widget):
        """Ends the applet"""
        sys.exit(0)

    def on_tasks_changed(self, tasks):
        print "on_tasks_changed"
        self.menu_add_tasks()
        self.search_dialog.refresh(self.database.get_tasks())
        self.dialog.refresh(self.database.get_tasks())

    def on_timer(self):
        """Timer handler which updates the list of tasks and the status."""
        gtk.timeout_add(FREQUENCY * 1000, self.on_timer)
        self.update_status()  # display current duration, etc

    def update_status(self):
        """Changes the indicator icon and text label according to running
        tasks."""
        tasks = [t for t in self.database.get_tasks() if "start" in t]

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
        for task in self.database.get_tasks():
            if "start" in task:
                ts = datetime.datetime.strptime(task["start"], "%Y%m%dT%H%M%SZ")
                duration += (now - ts)

        return int(duration.total_seconds())

    def format_duration(self, seconds):
        minutes = seconds / 60

        hours = minutes / 60
        minutes -= hours * 60

        return "%u:%02u" % (hours, minutes)


def main():
    # FIXME: find a better way to load icons
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    print os.getcwd()

    app = Checker()
    app.main()
    app.search_dialog.show_all()
    gtk.main()


if __name__ == "__main__":
    main()
