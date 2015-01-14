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
        self.database.start_task(self.selected_task_uuid)

    def _on_task_stop(self, item):
        self.database.stop_task(self.selected_task_uuid)

    def _on_task_edit(self, item):
        self.on_activate_task(self.selected_task_uuid)

    def _on_task_done(self, item):
        self.database.finish_task(self.selected_task_uuid)

    def _on_task_restart(self, item):
        self.database.restart_task(self.selected_task_uuid)

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
            str,   # 0 uuid
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
        if status == "pending":
            cell.set_property("foreground", "black")
        else:
            cell.set_property("foreground", "gray")

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
                  not not task.get("start"),
                  task["description"]]
            self.model.append(row)

        title = "Search for tasks (%u)" % len(tasks)
        self.set_title(title)

    def task_sort_func(self, task):
        # active tasksk are always first
        active = -task.is_active()

        # completed tasks are always last
        completed = task["status"] != "pending"

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
        uuid = model[row][0]
        self.on_activate_task(uuid)

    def _on_row_changed(self, view):
        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        tree_model, tree_iter = selection.get_selected()
        self.selected_task_uuid = tree_model.get_value(tree_iter, 0)
        util.log("Selected task {0}", self.selected_task_uuid)

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
        if uuid is None:
            util.log("Activate new task dialog")
            task = Task()
        else:
            util.log("Activate task {0}", uuid)
            task = self.database.get_task_info(uuid)

        Properties.show_task(self.database, task)


class Properties(gtk.Window):
    def __init__(self, database, debug=False):
        super(Properties, self).__init__()
        self.connect("delete_event", self.on_delete_event)
        self.connect("key-press-event", self._on_keypress)

        self.database = database
        self.debug = debug
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
        add_control(self.uuid, "UUID:")

        row += 1
        self.description = gtk.Entry()
        add_control(self.description, "Description:")

        row += 1
        self.project = Project()
        self.project.refresh(self.database.get_projects())
        add_control(self.project, "Project:")

        row += 1
        self.priority = Priority()
        add_control(self.priority, "Priority:")

        row += 1
        self.wait_date = gtk.Entry()
        add_control(self.wait_date, "Wait until:")

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
        if not self.task or not self.task.get("uuid"):
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

        if task.get("uuid"):
            dlg.show_existing_task(task)
        else:
            dlg.show_new_task(task)

        dlg.show_all()
        dlg.set_start_stop_label()

        def present():
            dlg.present()
            dlg.window.focus()
            dlg.grab_focus()
            dlg.description.grab_focus()

        gtk.idle_add(present)

    def show_existing_task(self, task):
        util.log("Showing task {0} ...", task["uuid"])

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
        util.log("Showing new task dialog...")

        self.uuid.set_text("")
        self.description.set_text("")
        self.project.set_text("")
        self.priority.set_text("M")
        self.tags.set_text("")
        self.completed.set_active(False)
        self._set_note("")

        self.description.grab_focus()

        self.start.set_label("Add")

    def _on_browse(self, widget):
        for word in self.task["description"].split(" "):
            if "://" in word:
                webbrowser.open(word)

    def on_close(self, widget):
        self.hide()

        self.save_task_note()

        updates = self.get_task_updates(self.task)
        if updates and updates.get("uuid"):
            self.update_task(updates)

        if self.debug:
            gtk.main_quit()

    def update_task(self, updates):
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
                util.log("New task uuid: {0}", uuid)
                break

    def save_task_note(self):
        if self.task:
            text = self._get_note()
            self.task.set_note(text)

    def _get_note(self):
        return self.notes.get_text()

    def _set_note(self, text):
        """Changes the contents of the note editor."""
        self.notes.set_text(text)

    def get_task_updates(self, task):
        update = {}

        if not self.task:
            return update

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

        tmp = self.wait_date.get_text()
        if tmp and tmp != self.task.get("wait"):
            pass

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
            util.log("new task not added: no changes.")
        else:
            util.log("new task: {0}", updates)
            uuid = self.callback(updates)
            if not isinstance(uuid, str):
                raise RuntimeError("Task editor callback must return an uuid.")

            if not self.task["uuid"]:
                self.task["uuid"] = uuid
                self.uuid.set_text(uuid)

    def on_task_start(self, task):
        util.log("task {0} start", self.task["uuid"])
        if task.get("uuid"):
            self.database.start_task(task["uuid"])

    def on_task_stop(self, task):
        util.log("task {0} stop", self.task["uuid"])
        if task.get("uuid"):
            self.database.stop_task(task["uuid"])
