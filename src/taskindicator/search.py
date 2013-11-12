# encoding=utf-8

from __future__ import print_function

import gtk

from taskindicator import util
from taskindicator.taskw import Task


class Dialog(gtk.Window):
    def __init__(self, parent=None):
        super(Dialog, self).__init__()
        self.query = None
        self.tasks = None
        self.setup_window()
        self.setup_controls()
        self.setup_signals()

    def setup_window(self):
        # self.set_title("Task search")
        self.set_border_width(4)
        self.set_default_size(600, 600)
        self.set_position(gtk.WIN_POS_CENTER)
        # self.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_REJECT)

        self.set_icon_name("taskui")

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
        self.connect("delete_event", self._on_delete)
        self.connect("key-press-event", self._on_keypress)

    def filter_tasks(self, model, iter):
        if self.query is None:
            return True

        project = model.get_value(iter, 2)
        if project and self.query in unicode(project, "utf-8").lower():
            return True

        description = model.get_value(iter, 3)
        if description and self.query in unicode(description, "utf-8").lower():
            return True

        return False

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

    def _on_delete(self, *args):
        """Instead of destroying the window on close, just hide it."""
        self.hide()
        return True

    def _on_row_activated(self, view, row, column):
        """Open a task editor dialog."""
        model = view.get_model()
        uuid = model[row][0]
        # self.hide()
        self.on_activate_task(uuid)

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
