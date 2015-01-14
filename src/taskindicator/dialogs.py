# encoding=utf-8

from __future__ import print_function

import gtk
import time
import webbrowser

from taskindicator import util
from taskindicator.controls import *


class Search(gtk.Window):
    def __init__(self, database, parent=None):
        super(Search, self).__init__()

        self.database = database
        self.query = None
        self.tasks = None
        self.selected_task_id = None
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
        self.set_task_active(True)
        self.database.start_task(self.selected_task_id)

    def _on_task_stop(self, item):
        self.set_task_active(False)
        self.database.stop_task(self.selected_task_id)

    def _on_task_edit(self, item):
        self.on_activate_task(self.selected_task_id)

    def _on_task_done(self, item):
        self.set_task_active(False, "completed")
        self.database.finish_task(self.selected_task_id)

    def _on_task_restart(self, item):
        self.set_task_active(True)
        self.database.restart_task(self.selected_task_id)

    def set_task_active(self, active, status=None):
        for row in self.model:
            if row[0] == self.selected_task_id:
                row[6] = active
                if status is not None:
                    row[1] = status

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

        self.model = model = gtk.ListStore(
            str,   # 0 id
            str,   # 1 status
            str,   # 2 project
            str,   # 3 clean description
            str,   # 4 urgency
            str,   # 5 priority
            bool,  # 6 started?
            str,   # 7 raw_description
            )

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

        # always show running tasks
        running = model[iter][6]
        if running:
            return True

        parts = []
        for field in (0, 2, 7):
            raw = model.get_value(iter, field)
            if raw:
                txt = unicode(raw, "utf-8")
                parts.append(txt.lower())
        fulltext = u" ".join(parts)

        for word in self.query.lower().split():
            if word.startswith("-"):
                if word[1:] in fulltext:
                    return False
            elif word not in fulltext:
                return False

        return True

    def cell_data(self, col, cell, model, iter, data=None):
        status = model[iter][1]
        if status in ("completed", "deleted"):
            cell.set_property("foreground", "gray")
        else:
            cell.set_property("foreground", "black")

        running = model[iter][6]
        if running:
            cell.set_property("weight", 800)
        else:
            cell.set_property("weight", 400)

    def refresh(self):
        """
        Updates the task list with the new tasks.  Also reloads the full task
        list, to show when the corresponding checkbox is checked.
        """
        tasks = self.database.get_tasks()
        self.tasks = [t for t in tasks if not t.is_closed()]
        self.all_tasks = [t for t in tasks if not t.is_deleted()]
        self.refresh_table()

    def refresh_table(self):
        if self.show_all_button.get_active():
            tasks = self.all_tasks
        else:
            tasks = self.tasks

        self.model.clear()
        for task in sorted(tasks, key=self.task_sort_func):
            row = [task.id(),
                  task["status"],
                  task.get_project(),
                  util.strip_description(task.get_summary()),
                  "%.1f" % float(task["urgency"]),
                  task.get("priority", "L"),
                  task.is_started(),
                  task.get_summary()]
            self.model.append(row)

        title = "Search for tasks (%u)" % len(tasks)
        self.set_title(title)

    def task_sort_func(self, task):
        # active tasksk are always first
        active = -task.is_active()

        # completed tasks are always last
        completed = task.is_closed()

        return (active, completed, -float(task["urgency"]))

    def show_all(self):
        super(Search, self).show_all()
        self.present()
        self.pmenu.show_all()

        def present():
            self.present()
            self.window.focus()
            self.grab_focus()
            self.query_ctl.grab_focus()

        gtk.idle_add(present)

    def _on_delete(self, *args):
        """Instead of destroying the window on close, just hide it."""
        self.hide()
        return True

    def _on_row_activated(self, view, row, column):
        """Open a task editor dialog."""
        model = view.get_model()
        task_id = model[row][0]
        self.on_activate_task(task_id)

    def _on_row_changed(self, view):
        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        tree_model, tree_iter = selection.get_selected()

        if not tree_iter:
            self.selected_task_id = None
            self.selected_task = None

        else:
            self.selected_task_id = tree_model.get_value(tree_iter, 0)
            util.log("Selected task {0}", self.selected_task_id)

            self.selected_task = None
            for task in self.all_tasks:
                if str(task.id()) == self.selected_task_id:
                    self.selected_task = task
                    if task.is_active():
                        self.pmenu_start.hide()
                        self.pmenu_stop.show()
                    else:
                        self.pmenu_start.show()
                        self.pmenu_stop.hide()

                    if task.is_closed():
                        self.pmenu_done.hide()
                        self.pmenu_restart.show()
                    else:
                        self.pmenu_done.show()
                        self.pmenu_restart.hide()

                    if "://" in task.get_summary():
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
        if uuid is None:
            util.log("Activate new task dialog")
            New.show_task(self.database)
        else:
            util.log("Activate task {0}", uuid)
            task = self.database.get_task_info(uuid)
            Properties.show_task(self.database, task)


class TaskDialog(gtk.Window):
    def __init__(self):
        super(TaskDialog, self).__init__()
        self.connect("key-press-event", self.on_keypress)

    def show_all(self):
        super(TaskDialog, self).show_all()

        def present():
            self.present()
            self.window.focus()
            self.grab_focus()
            self.description.grab_focus()

        gtk.idle_add(present)

    def on_keypress(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.destroy()
        if event.keyval == gtk.keysyms.Return:
            if not self.notes.has_focus():
                self.on_close(widget)


class New(TaskDialog):
    def __init__(self, database):
        super(New, self).__init__()
        self.connect("key-press-event", self.on_keypress)

        self.database = database

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
        self.description = gtk.Entry()
        add_control(self.description, "Summary:")

        row += 1
        self.project = gtk.Entry()  # Project()
        #self.project.refresh(self.database.get_projects())
        add_control(self.project, "Project:")

        row += 1
        self.priority = Priority()
        add_control(self.priority, "Priority:")

        row += 1
        self.notes = NoteEditor()
        add_control(self.notes, "Description:", vexpand=True)

        row += 1
        self.bbx = gtk.HButtonBox()
        self.grid.attach(self.bbx, 0, 2, row, row + 1,
            yoptions=gtk.FILL, xpadding=2, ypadding=2)

        self.start = gtk.Button("Save")
        self.start.connect("clicked", self.on_save)
        self.bbx.add(self.start)

        self.close = gtk.Button("Cancel")
        self.close.connect("clicked", self.on_close)
        self.bbx.add(self.close)

        self.set_title("Adding new task")
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_default_size(600, 400)

        self.set_icon_name("taskui")

    @classmethod
    def show_task(cls, database):
        """Opens the task editor dialog (new if no uuid)."""
        dlg = cls(database)
        dlg.show_all()

    def on_close(self, widget):
        self.destroy()

    def on_save(self, widget):
        self.database.add_task({
            "summary": self.description.get_text(),
            "description": self.notes.get_text(),
            "project": self.project.get_text(),
            "priority": self.priority.get_text(),
        })
        self.destroy()


class Properties(gtk.Window):
    def __init__(self, database):
        super(Properties, self).__init__()
        self.connect("delete_event", self.on_delete_event)

        self.database = database
        self.task = None

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
        add_control(self.uuid, "Task id:")

        row += 1
        self.description = gtk.Entry()
        add_control(self.description, "Summary:")

        row += 1
        self.project = gtk.Entry()  # Project()
        #self.project.refresh(self.database.get_projects())
        add_control(self.project, "Project:")

        row += 1
        self.priority = Priority()
        add_control(self.priority, "Priority:")

        row += 1
        self.notes = NoteEditor()
        add_control(self.notes, "Description:", vexpand=True)

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
        if not self.task or not self.task.id():
            label = "Add"
        elif self.task and "start" in self.task:
            dur = self.task.format_current_runtime()
            label = "Stop ({0})".format(dur)
        else:
            label = "Start"
        self.start.set_label(label)

    @classmethod
    def show_task(cls, database, task):
        """Opens the task editor dialog (new if no uuid)."""
        dlg = cls(database)
        dlg.task = task
        dlg.show_existing_task(task)
        dlg.show_all()
        dlg.set_start_stop_label()

    def show_existing_task(self, task):
        util.log("Showing task {0} ...", task.id())

        self.uuid.set_text(str(task.id()))
        self.description.set_text(task.get_summary())
        self.project.set_text(task["project"] or "")
        self.priority.set_text(str(task["priority"]))
        self.notes.set_text(task.get_description() or "")

        self.completed.set_active(task["status"] == "completed")

        if "start" in task:
            self.start.set_label("Stop")
        else:
            self.start.set_label("Start")

    def _on_browse(self, widget):
        for word in self.task.get_summary().split(" "):
            if "://" in word:
                webbrowser.open(word)

    def on_close(self, widget):
        self.database.update_task(self.task.id(), {
            "summary": self.description.get_text(),
            "project": self.project.get_text(),
            "priority": self.priority.get_text(),
            "description": self.notes.get_text(),
        })

        if self.completed.get_active():
            self.database.finish_task(self.task.id())

        self.destroy()

    def on_delete_event(self, widget, event, data=None):
        self.on_close(widget)
        return True

    def on_start_stop(self, widget):
        if self.task.is_active():
            self.database.stop_task(self.task.id())
            self.task.set_active(False)
        else:
            self.database.start_task(self.task.id())
            self.task.set_active(True)
        self.set_start_stop_label()
