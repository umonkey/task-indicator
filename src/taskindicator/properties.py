# encoding=utf-8

"""The task properties dialog."""


from __future__ import print_function

import re
import sys
import time
import webbrowser

import pygtk
pygtk.require("2.0")
import gtk

from taskindicator import util
from taskindicator.taskw import Task


__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"
__license__ = "GPL"


class Priority(gtk.ComboBox):
    """A combo-box with predefined contents, for editing task priority.
    Emulates get_text/set_text methods which work with H, M and L value,
    while the human-readable longer priority descriptions are displayed.
    """
    def __init__(self):
        super(Priority, self).__init__()

        self.store = gtk.ListStore(str, str)
        self.store.append(["H", "high"])
        self.store.append(["M", "medium (normal)"])
        self.store.append(["L", "low"])

        self.set_model(self.store)

        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, "text", 1)

    def set_text(self, value):
        """Sets the current priority.  Value can be H, M or L."""
        if value == "H":
            self.set_active(0)
        elif value == "L":
            self.set_active(2)
        else:
            self.set_active(1)

    def get_text(self):
        """Returns H, M or L, depending on the selected priority."""
        active = self.get_active()
        if active == 0:
            return "H"
        elif active == 2:
            return "L"
        else:
            return "M"


class Project(gtk.ComboBox):
    """Project selection combo box.
    TODO: make it editable, to allow adding new projects.
    """

    def __init__(self):
        self.value = None

        super(Project, self).__init__()
        self.store = gtk.ListStore(str)
        self.set_model(self.store)

        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, "text", 0)

        self.refresh()

    def refresh(self, projects=None):
        print("Refreshing project combo contents.")

        old_text = self.get_text()
        self.store.clear()
        if projects:
            projects = list(projects)  # copy
            projects.insert(0, "(none)")
            for project in sorted(projects):
                self.store.append([project])
        if old_text:
            self.set_text(old_text)

    def set_text(self, value):
        self.value = value

        for name in self.store:
            if value == name[0]:
                self.set_active(name.path[0])
                return

        self.set_active(0)
        print("Project set to {0}".format(value))

    def get_text(self):
        path = self.get_active()
        if path < 1:
            return None
        return self.store[path][0]


class NoteEditor(gtk.ScrolledWindow):
    def __init__(self):
        super(NoteEditor, self).__init__()
        self.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)

        self._tv = gtk.TextView()
        self._tv.set_wrap_mode(gtk.WRAP_WORD)
        self.add(self._tv)

    def set_text(self, text):
        self._tv.get_buffer().set_text(text)

    def get_text(self):
        buf = self._tv.get_buffer()
        text = buf.get_text(
            buf.get_start_iter(),
            buf.get_end_iter())
        return text

    def has_focus(self):
        return self._tv.has_focus()


class Tags(gtk.Entry):
    def get_tags(self):
        return [t for t in re.split(",\s*", self.get_text()) if t.strip()]


class Dialog(gtk.Window):
    def __init__(self, callback=None, debug=False):
        super(gtk.Window, self).__init__()
        self.connect("delete_event", self.on_delete_event)
        self.connect("key-press-event", self._on_keypress)

        self.debug = debug
        self.task = None
        self.callback = callback

        self.set_border_width(10)

        self.grid = gtk.Table(6, 2)
        self.add(self.grid)

        def add_label(text):
            l = gtk.Label(text)
            l.set_alignment(0, 0.5)
            self.grid.attach(l, 0, 1, row, row + 1,
                xoptions=gtk.FILL, yoptions=gtk.FILL, xpadding=2, ypadding=2)

        def add_control(ctl, label, vexpand=False):
            yoptions = gtk.FILL
            if vexpand:
                yoptions |= gtk.EXPAND

            self.grid.attach(ctl, 1, 2, row, row + 1,
                yoptions=yoptions, xpadding=2, ypadding=2)
            add_label(label)

        row = 0
        self.uuid = gtk.Entry()
        self.uuid.set_property("editable", False)
        add_control(self.uuid, "UUID:")

        row += 1
        self.description = gtk.Entry()
        add_control(self.description, "Description:")

        row += 1
        self.project = Project()
        add_control(self.project, "Project:")

        row += 1
        self.priority = Priority()
        add_control(self.priority, "Priority:")

        row += 1
        self.tags = Tags()
        add_control(self.tags, "Tags:")

        row += 1
        self.notes = NoteEditor()
        add_control(self.notes, "Notes:", vexpand=True)

        row += 1
        self.completed = gtk.CheckButton("completed")
        self.grid.attach(self.completed, 1, 2, row, row + 1,
            yoptions=gtk.FILL, xpadding=2, ypadding=2)

        row += 1
        self.bbx = gtk.HButtonBox()
        self.grid.attach(self.bbx, 0, 2, row, row + 1,
            yoptions=gtk.FILL, xpadding=2, ypadding=2)

        self.start = gtk.Button("Start")
        self.start.connect("clicked", self.on_start_stop)
        self.bbx.add(self.start)

        self.browse = gtk.Button("Open links")
        self.browse.connect("clicked", self._on_browse)
        self.bbx.add(self.browse)

        self.close = gtk.Button("Close")
        self.close.connect("clicked", self.on_close)
        self.bbx.add(self.close)

        self.set_title("Task properties")
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_default_size(600, 400)

        self.set_icon_name("taskui")

        self.on_timer()

    def on_timer(self):
        """Updates the start/stop button periodically."""
        gtk.timeout_add(1000, self.on_timer)

        if self.get_property("visible"):
            self.set_start_stop_label()

    def set_start_stop_label(self):
        """Updates the start/stop button label according to the current task
        activity status.  If the task is running, then the label is "Stop" and
        the running time is displayed."""
        if not self.task.get("uuid"):
            label = "Add"
        elif self.task and "start" in self.task:
            dur = self.task.format_current_runtime()
            label = "Stop ({0})".format(dur)
        else:
            label = "Start"
        self.start.set_label(label)

    def show_task(self, task):
        """Opens the task editor dialog (new if no uuid)."""
        if isinstance(task, dict):
            task = Task(task)
        elif not isinstance(task, dict):
            raise ValueError("task must be a dict or a taskw.Task")

        self.task = task

        if task.get("uuid"):
            self.show_existing_task(task)
        else:
            self.show_new_task(task)

        self.show_all()
        self.set_start_stop_label()
        self.description.grab_focus()

    def show_existing_task(self, task):
        print("Showing task {0} ...".format(task["uuid"]), file=sys.stderr)

        self.uuid.set_text(task["uuid"])
        self.description.set_text(task["description"])
        self.project.set_text(task["project"])
        self.priority.set_text(task["priority"])
        self.tags.set_text(", ".join(task["tags"]))
        self._set_note(task.get_note())

        self.completed.set_active(task["status"] == "completed")

        if "start" in task:
            self.start.set_label("Stop")
        else:
            self.start.set_label("Start")

    def show_new_task(self, task):
        print("Showing new task dialog...", file=sys.stderr)

        self.uuid.set_text("")
        self.description.set_text("")
        self.project.set_text("")
        self.priority.set_text("M")
        self.tags.set_text("")
        self.completed.set_active(False)
        self._set_note("")

        self.description.grab_focus()

        self.start.set_label("Add")

    def refresh(self, tasks):
        """Builds the list of all used project names and feeds it to the
        project editor combo box."""
        projects = {}
        for task in tasks:
            projects[task["project"]] = True
        self.project.refresh(projects.keys())

    def _on_browse(self, widget):
        for word in self.task["description"].split(" "):
            if "://" in word:
                webbrowser.open(word)

    def on_close(self, widget):
        self.hide()

        self.save_task_note()
        if self.callback:
            updates = self.get_task_updates(self.task)
            if updates and updates.get("uuid"):
                self.callback(updates)

        if self.debug:
            gtk.main_quit()

    def save_task_note(self):
        text = self._get_note()
        self.task.set_note(text)

    def _get_note(self):
        return self.notes.get_text()

    def _set_note(self, text):
        """Changes the contents of the note editor."""
        self.notes.set_text(text)

    def get_task_updates(self, task):
        update = {}

        if task.get("uuid"):
            update["uuid"] = task["uuid"]

        tmp = self.description.get_text()
        if tmp is not None and tmp != self.task.get("description"):
            update["description"] = tmp

        tmp = self.project.get_text()
        if tmp is not None and tmp != self.task.get("project"):
            update["project"] = tmp

        tmp = self.priority.get_text()
        if tmp is not None and tmp != self.task.get("priority"):
            update["priority"] = tmp

        tmp = "completed" if self.completed.get_active() else "pending"
        if tmp is not None and tmp != self.task.get("status"):
            update["status"] = tmp

        tmp = self.tags.get_tags()
        old_tags = self.task["tags"]
        if tmp is not None and tmp != old_tags:
            update["tags"] = []
            for k in old_tags:
                if k not in tmp:
                    update["tags"].append("-" + k)
            for k in tmp:
                if k not in old_tags:
                    update["tags"].append("+" + k)

        return update

    def on_delete_event(self, widget, event, data=None):
        self.on_close(widget)
        return True

    def _on_keypress(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide()
        if event.keyval == gtk.keysyms.Return:
            if not self.notes.has_focus():
                self.on_close(widget)

    def on_start_stop(self, widget):
        if not self.task.get("uuid"):
            self.on_task_add(self.task)
        elif "start" in self.task:
            self.on_task_stop(self.task)
            del self.task["start"]
        else:
            self.on_task_start(self.task)
            self.task["start"] = int(time.time())
        # self.on_close(widget)

    def on_task_add(self, task):
        updates = self.get_task_updates(task)
        if not updates:
            print("new task not added: no changes.", file=sys.stderr)
        else:
            print("new task: {0}".format(updates), file=sys.stderr)
            uuid = self.callback(updates)
            if not isinstance(uuid, str):
                raise RuntimeError("Task editor callback must return an uuid.")

            if not self.task["uuid"]:
                self.task["uuid"] = uuid
                self.uuid.set_text(uuid)

    def on_task_start(self, task):
        print("task {0} start".format(self.task["uuid"]),
            file=sys.stderr)

    def on_task_stop(self, task):
        print("task {0} stop".format(self.task["uuid"]),
            file=sys.stderr)


def main():
    def take2(task):
        if len(task) > 1:
            print("Task update: {0}".format(task),
                file=sys.stderr)

    w = Dialog(callback=take2, debug=True)
    w.show_task({"uuid": "2ea544b9-a068-4e3e-a99d-5235ed53a17f",
            "description": "Hello, world.",
            "project": "oss.taskwarrior",
            "tags": "hobby, linux",
            "start": "20130203T163010Z",
            "status": "completed"})
    gtk.main()


if __name__ == "__main__":
    main()
