#!/usr/bin/env python

"""TaskWarrior active task count and duration indicator applet.
"""

from __future__ import print_function

__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"


import appindicator
import datetime
import dateutil.parser
import json
import os
import re
import sys
import time

import pygtk
pygtk.require("2.0")
import gtk

from taskindicator import database
from taskindicator import properties
from taskindicator import search
from taskindicator import taskw
from taskindicator import util


FREQUENCY = 1  # seconds


def get_program_path(command):
    for path in os.getenv("PATH").split(os.pathsep):
        full = os.path.join(path, command)
        if os.path.exists(full):
            return full


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
            self.icon, appindicator.CATEGORY_APPLICATION_STATUS)

        icondir = os.getenv("TASK_INDICATOR_ICONDIR")
        if icondir:
            self.indicator.set_icon_theme_path(icondir)
            print("Appindicator theme path: {0}, wanted: {1}".format(
                self.indicator.get_icon_theme_path(), icondir))

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
        util.run_command(["task", task["uuid"], "start"])
        self.update_status()

    def on_stop_task(self, task):
        util.run_command(["task", task["uuid"], "stop"])
        self.update_status()

    def menu_setup(self):
        self.menu = gtk.Menu()

        def add_item(text, handler):
            item = gtk.MenuItem(text)
            item.connect("activate", handler)
            item.show()
            self.menu.append(item)
            return item

        self.add_task_item = add_item("Add new task...", self.on_add_task)
        self.show_all_item = add_item("Show more...", self.on_show_all_tasks)
        self.stop_item = add_item("Stop all running tasks", self.stop)
        if get_program_path("bugwarrior-pull"):
            self.bw_item = add_item("Pull tasks from outside",
                self.on_pull_tasks)
        self.quit_item = add_item("Quit", self.quit)

    def menu_add_tasks(self):
        print("Updating menu contents.", file=sys.stderr)

        for item in self.menu.get_children():
            if item.get_data("is_dynamic"):
                self.menu.remove(item)
        self.task_items = []

        data = [t for t in self.database.get_tasks()
            if t["status"] == "pending"]

        for task in sorted(data, key=self.task_sort)[:10]:
            item = gtk.CheckMenuItem(self.format_menu_label(task),
                use_underline=False)
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
        title = util.strip_description(task["description"])
        if "project" in task:
            title += u" [{0}]".format(
                task["project"].split(".")[-1])
        return title

    def task_sort(self, task):
        """Returns the data to sort tasks by."""
        is_pinned = "pin" in task.get("tags", [])
        is_running = "start" in task
        is_endless = "endless" in task.get("tags", [])
        pri = {"H": 3, "M": 2, "L": 1}.get(task.get("priority"), 0)
        return (-is_running, -is_pinned, is_endless, -pri,
            -float(task.get("urgency", 0)))

    def on_add_task(self, widget):
        self.dialog.show_task({"uuid": None, "status": "pending",
            "description": "", "priority": "M"})

    def on_pull_tasks(self, widget):
        util.run_command(["bugwarrior-pull"])

    def on_show_all_tasks(self, widget):
        self.search_dialog.show_all()

    def on_search_callback(self, uuid):
        """Called when opening a task in the search window."""
        if uuid is None:
            task = taskw.Task()
        else:
            task = util.get_task_info(uuid)
        self.dialog.show_task(task)

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
        if "uuid" in updates:
            uuid = updates["uuid"]
            del updates["uuid"]
        else:
            uuid = None

        if uuid:
            command = ["task", uuid, "mod"]
        else:
            command = ["task", "add"]

        if updates:
            for k, v in updates.items():
                if k == "tags":
                    for tag in v:
                        if tag.strip():
                            command.append(tag)
                elif k == "description":
                    command.append(v)
                else:
                    command.append("{0}:{1}".format(k, v))
            output = util.run_command(command)

            for _taskno in re.findall("Created task (\d+)", output):
                uuid = util.run_command(["task", _taskno, "uuid"]).strip()
                print("New task uuid: {0}".format(uuid),
                    file=sys.stderr)
                break

        self.update_status()
        return uuid

    def main(self):
        """Enters the main program loop"""
        self.on_timer()

    def stop(self, widget):
        """Stops running tasks"""
        for task in self.database.get_tasks():
            if "start" in task:
                util.run_command(["task", task["uuid"], "stop"])
        self.stop_item.hide()
        self.update_status()

    def quit(self, widget):
        """Ends the applet"""
        sys.exit(0)

    def on_tasks_changed(self, tasks):
        print("on_tasks_changed", file=sys.stderr)
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
        tasks = [t for t in self.database.get_tasks()
            if t["status"] == "pending" and "start" in t]

        if not tasks:
            self.indicator.set_label("Idle")
            self.indicator.set_status(appindicator.STATUS_ACTIVE)
            self.stop_item.hide()
        else:
            self.indicator.set_status(appindicator.STATUS_ATTENTION)
            self.stop_item.show()

            msg = "{0}/{1}".format(len(tasks),
                self.format_duration(self.get_duration()))

            self.indicator.set_label(msg)

    def get_duration(self):
        duration = 0
        for task in self.database.get_tasks():
            if task["status"] == "pending" and "start" in task:
                duration += task.get_current_runtime()
        return duration

    def format_duration(self, seconds):
        minutes = seconds / 60

        hours = minutes / 60
        minutes -= hours * 60

        return "%u:%02u" % (hours, minutes)


def main():
    os.chdir("/")

    app = Checker()
    app.main()
    app.search_dialog.show_all()
    gtk.main()
