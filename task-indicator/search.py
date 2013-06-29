# encoding=utf-8

import gtk


class Dialog(gtk.Dialog):
    def __init__(self, parent=None):
        super(Dialog, self).__init__("Search for tasks", parent=parent)
        self.query = None
        self.setup_window()
        self.setup_controls()
        self.setup_signals()

    def setup_window(self):
        # self.set_title("Task search")
        self.set_border_width(2)
        self.set_default_size(600, 600)
        self.set_position(gtk.WIN_POS_CENTER)
        self.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_REJECT)

        self.set_icon_from_file("taskui.svg")

    def setup_controls(self):
        self.query_ctl = gtk.Entry()
        self.query_ctl.connect("changed", self._on_query_changed)
        self.vbox.pack_start(self.query_ctl, expand=False, fill=True, padding=4)

        self.model = model = gtk.ListStore(str, str, str, str, str, str)
        self.model_filter = model_filter = model.filter_new()
        model_filter.set_visible_func(self.filter_tasks)

        view = gtk.TreeView()
        view.set_model(model_filter)
        view.connect("row_activated", self._on_row_activated)

        col = gtk.TreeViewColumn("Project", gtk.CellRendererText(), text=2)
        view.append_column(col)

        cell = gtk.CellRendererText()
        cell.set_property("xalign", 1.0)
        col = gtk.TreeViewColumn("Urg.", cell, text=4)
        view.append_column(col)

        cell = gtk.CellRendererText()
        cell.set_property("xalign", 0.5)
        col = gtk.TreeViewColumn("Pri", cell, text=5)
        view.append_column(col)

        col = gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=3)
        view.append_column(col)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scroll.add_with_viewport(view)

        self.vbox.add(scroll)

    def setup_signals(self):
        self.connect("response", self._on_response)
        self.connect("delete_event", self._on_delete)
        self.connect("key-press-event", self._on_keypress)

    def filter_tasks(self, model, iter):
        # print "filter_tasks", model, iter
        if self.query is None:
            return True

        project = model.get_value(iter, 2)
        if project and self.query in unicode(project, "utf-8").lower():
            return True

        description = model.get_value(iter, 3)
        if description and self.query in unicode(description, "utf-8").lower():
            return True

        return False

    def refresh(self, tasks):
        """Updates the task list with the new tasks."""
        self.model.clear()
        for task in sorted(tasks, key=lambda t: -float(t["urgency"])):
            description = task["description"]
            if description.startswith("(bw)"):
                words = description.split(" ")
                description = " ".join(words[2:])

            self.model.append([task["uuid"], task["id"],
                task["project"], description,
                "%.1f" % float(task["urgency"]),
                task["priority"]])

        title = "Search for tasks (%u)" % len(tasks)
        self.set_title(title)

    def show_all(self):
        super(Dialog, self).show_all()
        self.grab_focus()

    def _on_delete(self, *args):
        """Instead of destroying the window on close, just hide it."""
        self.hide()
        return True

    def _on_row_activated(self, view, row, column):
        model = view.get_model()
        uuid = model[row][0]
        self.hide()
        self.on_activate_task(uuid)

    def _on_query_changed(self, ctl):
        """Handles the query change.  Stores the new query in self.query for
        quicker access, then refilters the tree."""
        self.query = unicode(ctl.get_text(), "utf-8").lower()
        self.model_filter.refilter()

    def _on_response(self, event, response_id):
        self.hide()

    def _on_keypress(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide()

    def on_activate_task(self, uuid):
        print "Activate task %s" % uuid
