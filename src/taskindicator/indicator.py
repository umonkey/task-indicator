#!/usr/bin/env python

"""TaskWarrior active task count and duration indicator applet.
"""

from __future__ import print_function

__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"


import datetime
import dateutil.parser
import json
import os
import re
import signal
import subprocess
import sys
import time

import pygtk
pygtk.require("2.0")
import gtk

try:
    import appindicator
    HAVE_APPINDICATOR = True
except ImportError:
    HAVE_APPINDICATOR = False

from taskindicator import database
from taskindicator import properties
from taskindicator import search
from taskindicator import taskw
from taskindicator import util


FREQUENCY = 1  # seconds


def log(msg):
    print(msg, file=sys.stderr)


def get_program_path(command):
    for path in os.getenv("PATH").split(os.pathsep):
        full = os.path.join(path, command)
        if os.path.exists(full):
            return full


class BaseIndicator(object):
    # http://www.pygtk.org/pygtk2reference/gtk-stock-items.html
    ACTIVE_ICON = gtk.STOCK_MEDIA_PLAY

    def __init__(self):
        self.stop_item = None
        self.task_items = []

        self.setup_menu()
        self.setup_icon()

    def setup_menu(self):
        """
        Setup the tray menu

        Adds action menu items and task placeholders, which are later
        replaced with real recently modified tasks (see set_tasks).
        """
        self.menu = gtk.Menu()

        def add_item(label, handler, icon=None):
            if icon is None:
                item = gtk.MenuItem()
            else:
                item = gtk.ImageMenuItem(icon)
            item.set_label(label)
            item.connect("activate", handler)
            item.show()
            self.menu.append(item)
            return item

        self.task_items = []
        for x in range(10):
            item = gtk.ImageMenuItem()
            item.set_label("task placeholder")
            item.connect("activate",
                         lambda item: self.on_task_selected(item.get_data("task")))
            self.menu.append(item)
            self.task_items.append(item)

        self.separator = gtk.SeparatorMenuItem()
        self.menu.append(self.separator)

        add_item("Add new task...",
            lambda *args: self.on_add_task(),
            gtk.STOCK_NEW)
        add_item("Search tasks...",
            lambda *args: self.on_toggle(),
            gtk.STOCK_FIND)
        self.stop_item = add_item("Stop all running tasks",
            lambda *args: self.on_stop_all(),
            gtk.STOCK_STOP)
        if self.can_pull():
            add_item("Pull tasks",
                lambda *args: self.on_pull(),
                gtk.STOCK_REFRESH)
        add_item("Quit",
            lambda *args: self.on_quit(),
            gtk.STOCK_QUIT)

    def setup_icon(self):
        log("WARNING: setup_icon not implimented")

    def set_tasks(self, tasks):
        """
        Update tasks in the tray menu

        Updates placeholder menu items with real data, proper icons and
        visibility.
        """
        for idx, item in enumerate(self.task_items):
            if idx > len(tasks):
                item.hide()
            else:
                task = tasks[idx]
                desc = util.strip_description(task["description"])

                if task.is_active():
                    label = item.get_children()[0]
                    label.set_markup("<b>%s</b>" % desc)

                    icon = gtk.image_new_from_stock(self.ACTIVE_ICON,
                                                    gtk.ICON_SIZE_MENU)
                    item.set_image(icon)
                else:
                    item.set_label(desc)
                    item.set_image(None)

                item.set_data("task", task)
                item.show()

        if tasks:
            self.separator.show()
        else:
            self.separator.hide()

    def can_pull(self):
        return get_program_path("task-pull") != None

    def on_quit(self):
        log("on_quit not handled")

    def on_toggle(self):
        log("on_toggle not handled")

    def on_add_task(self):
        log("on_add_task not handled")

    def on_stop_all(self):
        log("on_stop_all not handled")

    def on_task_selected(self, task):
        log("on_task_selected not handled, %s" % task)

    def on_pull(self):
        log("on_pull not handled")


class UbuntuIndicator(BaseIndicator):
    """
    AppIndicator based icon

    Used only if appindicator is available and running.
    """
    appname = "task-indicator"
    icon = "taskui"
    icon_attn = "taskui-active"

    def setup_icon(self):
        self.indicator = appindicator.Indicator(self.appname,
            self.icon, appindicator.CATEGORY_APPLICATION_STATUS)

        icondir = os.getenv("TASK_INDICATOR_ICONDIR")
        if icondir:
            self.indicator.set_icon_theme_path(icondir)
            # log("Appindicator theme path: {0}, wanted: {1}".format(self.indicator.get_icon_theme_path(), icondir))

        self.indicator.set_status(appindicator.STATUS_ACTIVE)
        self.indicator.set_attention_icon(self.icon_attn)

        self.indicator.set_menu(self.menu)

    def set_idle(self):
        self.indicator.set_label("Idle")
        self.indicator.set_status(appindicator.STATUS_ACTIVE)
        self.stop_item.hide()

    def set_running(self, count, duration):
        self.indicator.set_status(appindicator.STATUS_ATTENTION)
        self.stop_item.show()

        msg = "{0}/{1}".format(count, duration)
        self.indicator.set_label(msg)

    @classmethod
    def is_available(cls):
        if not HAVE_APPINDICATOR:
            log("No appindicator package.")
            return False  # not installed

        user = os.getenv("USER")

        p = subprocess.Popen(["pgrep", "-u", user, "indicator-applet"],
            stdout=subprocess.PIPE)
        out = p.communicate()[0]

        if out.strip() == "":
            log("User %s has no indicator-applet running." % user)
            return False  # not running

        return True


class GtkIndicator(BaseIndicator):
    def setup_icon(self):
        self.icon = gtk.StatusIcon()
        self.icon.set_from_icon_name("taskui")
        self.icon.connect("activate",
                          lambda *args: self.on_toggle())
        self.icon.connect("popup-menu", self.on_menu)
        self.icon.set_tooltip("TaskWarrior")

    def on_menu(self, icon, button, click_time):
        self.menu.popup(None, None, gtk.status_icon_position_menu, button, click_time, self.icon)

    def set_idle(self):
        self.icon.set_from_icon_name("taskui")
        self.icon.set_tooltip("No running tasks")
        self.stop_item.hide()

    def set_running(self, count, duration):
        self.icon.set_from_icon_name("taskui-active")
        self.stop_item.show()

        if count == 1:
            self.icon.set_tooltip("%s" % duration)
        else:
            self.icon.set_tooltip("%u tasks, %s" % (count, duration))


class Checker(object):
    """The indicator applet.  Displays the TaskWarrior icon and current
    activity time, if any.  The pop-up menu can be used to start or stop
    running tasks.
    """

    def __init__(self):
        self.toggle_lock = False

        self.setup_indicator()

        self.database = database.Database(callback=self.on_tasks_changed)

        self.dialog = properties.Dialog(callback=self.on_task_info_closed)
        self.dialog.on_task_start = self.on_start_task
        self.dialog.on_task_stop = self.on_stop_task

        self.search_dialog = search.Dialog()
        self.search_dialog.on_activate_task = self.on_search_callback

        self.database.start_polling()

    def setup_indicator(self):
        if UbuntuIndicator.is_available():
            log("AppIndicator is available, using it.")
            self.indicator = UbuntuIndicator()
        else:
            log("AppIndicator is not available, using Gtk status icon.")
            self.indicator = GtkIndicator()

        self.indicator.on_add_task = self.on_add_task
        self.indicator.on_toggle = self.on_toggle_search
        self.indicator.on_stop_all = self.on_stop_all
        self.indicator.on_quit = self.on_quit
        self.indicator.on_pull = self.on_pull
        self.indicator.on_task_selected = self.on_task_selected

    def on_start_task(self, task):
        util.run_command(["task", task["uuid"], "start"])
        self.update_status()

    def on_stop_task(self, task):
        util.run_command(["task", task["uuid"], "stop"])
        self.update_status()

    def menu_add_tasks(self):
        tasks = filter(lambda t: t["status"] == "pending",
                       self.database.get_tasks())

        tasks = sorted(tasks,
                       key=lambda t: t["modified"],
                       reverse=True)

        self.indicator.set_tasks(tasks)

    def on_add_task(self):
        self.dialog.show_task({"uuid": None, "status": "pending",
            "description": "", "priority": "M"})

    def on_pull(self):
        p = subprocess.Popen(["x-terminal-emulator", "-e", "task-pull"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    def on_toggle_search(self, *args):
        if self.search_dialog.get_property("visible"):
            self.search_dialog.hide()
        else:
            self.search_dialog.show_all()

    def on_search_callback(self, uuid):
        """Called when opening a task in the search window."""
        if uuid is None:
            task = taskw.Task()
        else:
            task = util.get_task_info(uuid)
        self.dialog.show_task(task)

    def on_task_selected(self, task):
        log("task selected: %s" % task)
        if task:
            self.dialog.show_task(task)

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

        def handle(*args, **kwargs):
            log("Got signal USR1, showing the search dialog.")
            self.search_dialog.show_all()

        signal.signal(signal.SIGUSR1, handle)

    def on_stop_all(self):
        """Stops running tasks"""
        self.indicator.set_idle()

        def timer():
            for task in self.database.get_tasks():
                if "start" in task:
                    util.run_command(["task", task["uuid"], "stop"])
            self.update_status()

        gtk.idle_add(timer)

    def on_quit(self):
        """Ends the applet"""
        sys.exit(0)

    def on_tasks_changed(self, tasks):
        log("on_tasks_changed")
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
            self.indicator.set_idle()
        else:
            count = len(tasks)
            duration = self.format_duration(self.get_duration())
            self.indicator.set_running(count, duration)

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


def show_existing_instance():
    """
    Open up the previous instance, if there is one.

    FIXME: use dbus.
    """
    p = subprocess.Popen(["pgrep", "-f", "/task-indicator"],
                         stdout=subprocess.PIPE)

    out = p.communicate()[0]
    for line in out.splitlines():
        if line.strip().isdigit():
            pid = int(line.strip())
            if pid != os.getpid():
                try:
                    os.kill(pid, signal.SIGUSR1)
                    log("Sent SIGUSR1 to process %u." % pid)
                    return True
                except Exception, e:
                    log("Error sending SIGUSR1 to process %u: %s" % (pid, e))

    return False


def main():
    if show_existing_instance():
        return

    os.chdir("/")

    app = Checker()
    app.main()
    # app.search_dialog.show_all()
    gtk.main()
