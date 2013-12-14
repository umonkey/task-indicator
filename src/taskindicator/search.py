# encoding=utf-8

from __future__ import print_function

import gtk
import subprocess
import sys
import webbrowser

from taskindicator import util
from taskindicator.taskw import Task


class Dialog(gtk.Window):
    def __init__(self, parent=None):
        super(Dialog, self).__init__()
        self.query = None
        self.tasks = None
        self.selected_task_uuid = None
        self.selected_task = None

        self.setup_window()
        self.setup_controls()
        self._setup_popup_menu()
        self.setup_signals()

    def setup_window(self):
        # self.set_title("Task search")
        self.set_border_width(4)
        self.set_default_size(600, 600)
        self.set_position(gtk.WIN_POS_CENTER)
        # self.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_REJECT)

        self.set_icon_name("taskui")

    def _setup_popup_menu(self):
        self.pmenu = gtk.Menu()

        def add_item(label, handler):
            item = gtk.MenuItem(label)
            item.connect("activate", handler)
            self.pmenu.append(item)
            return item

        self.pmenu_start = add_item("Start", self._on_task_start)
        self.pmenu_stop = add_item("Stop", self._on_task_stop)
        self.pmenu_edit = add_item("Edit", self._on_task_edit)
        self.pmenu_done = add_item("Done", self._on_task_done)
        self.pmenu_restart = add_item("Restart", self._on_task_restart)
        self.pmenu_links = add_item(
            "Open linked web page", self._on_task_links)

    def _on_popup_menu(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.pmenu.popup(None, None, None, event.button, event.time)

    def _on_task_start(self, item):
        print("Starting task %s ..." % self.selected_task_uuid)
        subprocess.Popen(["task", self.selected_task_uuid, "start"]).wait()

    def _on_task_stop(self, item):
        print("Stopping task %s ..." % self.selected_task_uuid)
        subprocess.Popen(["task", self.selected_task_uuid, "stop"]).wait()

    def _on_task_edit(self, item):
        self.on_activate_task(self.selected_task_uuid)

    def _on_task_done(self, item):
        print("Finishing task %s ..." % self.selected_task_uuid)
        subprocess.Popen(["task", self.selected_task_uuid, "stop"]).wait()
        subprocess.Popen(["task", self.selected_task_uuid, "done"]).wait()

    def _on_task_restart(self, item):
        print("Restarting task %s ..." % self.selected_task_uuid)
        subprocess.Popen(["task", self.selected_task_uuid,
            "mod", "status:pending"]).wait()

    def _on_task_links(self, item):
        if self.selected_task:
            for part in self.selected_task["description"].split():
                if "://" in part:
                    webbrowser.open(part)

    def setup_controls(self):
        self.vbox = gtk.VBox(homogeneous=False, spacing=4)
        self.add(self.vbox)

        self.query_ctl = gtk.Entry()
        self.query_ctl.connect("changed", self._on_query_changed)
        self.vbox.pack_start(self.query_ctl, expand=False,
            fill=True, padding=4)

        self.model = model = gtk.ListStore(str, str, str, str, str, str, bool)
        self.model_filter = model_filter = model.filter_new()
        model_filter.set_visible_func(self.filter_tasks)

        view = gtk.TreeView()
        view.set_model(model_filter)
        view.connect("row_activated", self._on_row_activated)
        view.connect("cursor-changed", self._on_row_changed)
        self.tv = view

        lcell = gtk.CellRendererText()
        lcell.set_property("xalign", 0.0)

        mcell = gtk.CellRendererText()
        mcell.set_property("xalign", 0.5)

        rcell = gtk.CellRendererText()
        rcell.set_property("xalign", 1.0)

        def add_column(text, cell, data_idx):
            col = gtk.TreeViewColumn(text, cell, text=data_idx)
            col.set_cell_data_func(cell, self.cell_data)
            # col.set_sort_column_id(data_idx)
            view.append_column(col)

        add_column("Project", lcell, 2)
        add_column("Urg", rcell, 4)
        add_column("Pri", mcell, 5)
        add_column("Description", lcell, 3)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        # scroll.add_with_viewport(view)
        scroll.add(view)

        self.vbox.pack_start(scroll, expand=True, fill=True)

        self.setup_bottom_controls()

    def setup_bottom_controls(self):
        """Fills in the bottom bar (checkboxes and buttons)."""
        hbox = gtk.HBox(homogeneous=False, spacing=4)
        self.vbox.pack_start(hbox, expand=False, fill=True)

        self.show_all_button = gtk.CheckButton("Show completed")
        hbox.pack_start(self.show_all_button, expand=True, fill=True)

        self.close_button = gtk.Button("Close")
        hbox.pack_end(self.close_button, expand=False, fill=False)

        self.add_button = gtk.Button("Add...")
        hbox.pack_end(self.add_button, expand=False, fill=False)

    def setup_signals(self):
        self.add_button.connect("clicked", self._on_add_clicked)
        self.close_button.connect("clicked", self._on_close)
        self.show_all_button.connect("clicked", self._on_show_all)
        self.tv.connect("event", self._on_popup_menu)
        self.connect("delete_event", self._on_delete)
        self.connect("key-press-event", self._on_keypress)

    def filter_tasks(self, model, iter):
        if self.query is None:
            return True

        parts = []
        for field in (2, 3):
            txt = unicode(model.get_value(iter, field), "utf-8")
            parts.append(txt.lower())
        fulltext = u" ".join(parts)

        for word in self.query.lower().split():
            if word not in fulltext:
                return False

        return True

    def cell_data(self, col, cell, model, iter, data=None):
        status = model[iter][1]
        if status == "pending":
            cell.set_property("foreground", "black")
        else:
            cell.set_property("foreground", "gray")

        running = model[iter][6]
        if running:
            cell.set_property("weight", 800)
        else:
            cell.set_property("weight", 400)

    def refresh(self, tasks):
        """Updates the task list with the new tasks.  Also reloads the full
        task list, to show when the corresponding checkbox is checked."""
        self.tasks = [t for t in tasks if t["status"] == "pending"]
        self.all_tasks = [t for t in tasks if t["status"] != "deleted"]
        self.refresh_table()

    def refresh_table(self):
        if self.show_all_button.get_active():
            tasks = self.all_tasks
        else:
            tasks = self.tasks

        self.model.clear()
        for task in sorted(tasks, key=self.task_sort_func):
            row = [task["uuid"],
                  task["status"],
                  task["project"],
                  util.strip_description(task["description"]),
                  "%.1f" % float(task["urgency"]),
                  task.get("priority", "L"),
                  not not task.get("start")]
            self.model.append(row)

        title = "Search for tasks (%u)" % len(tasks)
        self.set_title(title)

    def task_sort_func(self, task):
        completed = task["status"] != "pending"
        return (completed, -float(task["urgency"]))

    def show_all(self):
        super(Dialog, self).show_all()
        self.present()
        self.grab_focus()
        self.pmenu.show_all()

    def _on_delete(self, *args):
        """Instead of destroying the window on close, just hide it."""
        self.hide()
        return True

    def _on_row_activated(self, view, row, column):
        """Open a task editor dialog."""
        model = view.get_model()
        uuid = model[row][0]
        self.on_activate_task(uuid)

    def _on_row_changed(self, view):
        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        tree_model, tree_iter = selection.get_selected()
        self.selected_task_uuid = tree_model.get_value(tree_iter, 0)
        print("Selected task %s" % self.selected_task_uuid,
            file=sys.stderr)

        self.selected_task = None
        for task in self.all_tasks:
            if task["uuid"] == self.selected_task_uuid:
                self.selected_task = task
                if task.is_active():
                    self.pmenu_start.hide()
                    self.pmenu_stop.show()
                else:
                    self.pmenu_start.show()
                    self.pmenu_stop.hide()

                if task["status"] == "pending":
                    self.pmenu_done.show()
                    self.pmenu_restart.hide()
                else:
                    self.pmenu_done.hide()
                    self.pmenu_restart.show()

                if "://" in task["description"]:
                    self.pmenu_links.show()
                else:
                    self.pmenu_links.hide()

    def _on_query_changed(self, ctl):
        """Handles the query change.  Stores the new query in self.query for
        quicker access, then refilters the tree."""
        self.query = unicode(ctl.get_text(), "utf-8").lower()
        self.model_filter.refilter()

    def _on_close(self, widget):
        self.hide()

    def _on_add_clicked(self, widget):
        self.on_activate_task(None)

    def _on_show_all(self, widget):
        self.refresh_table()

    def _on_keypress(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide()

    def on_activate_task(self, uuid):
        print("Activate task {0}".format(uuid),
            file=sys.stderr)
