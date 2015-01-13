# encoding=utf-8

"""The task properties dialog."""


from __future__ import print_function

import re

import pygtk
pygtk.require("2.0")
import gtk


__author__ = "Justin Forest"
__email__ = "hex@umonkey.net"
__license__ = "GPL"

__all__ = [
    "Priority",
    "Project",
    "NoteEditor",
    "Tags",
]


class Priority(gtk.ComboBox):
    """
    A combo-box with predefined contents, for editing task priority.
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
    """
    Project selection combo box.
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
