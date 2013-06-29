# encoding=utf-8

import gtk
import json
import os
import shlex

from util import run_command


FREQUENCY = 1


class Database(object):
    def __init__(self, callback=None):
        self.filename = self.get_filename()
        self.mtime = None
        self.tasks = None

        self.callback = callback

    def start_polling(self):
        self._on_timeout()

    def poll(self):
        """Returns True if the file was updated since last check."""
        mtime = os.stat(self.filename).st_mtime
        if mtime != self.mtime:
            print "Task database file modified."
            self.tasks = None
            self.mtime = mtime
            return True
        return False

    def get_filename(self):
        for line in run_command(["task", "_show"]).split("\n"):
            if line.startswith("data.location="):
                folder = line.split("=", 1)[1].strip()
                return os.path.join(folder, "pending.data")

    def get_tasks(self):
        if self.tasks is None:
            print "Reloading tasks."
            self.tasks = self.load_tasks()
        return self.tasks

    def load_tasks(self):
        f = self.get_task_filter()
        output = run_command(["task", "rc.json.array=1"] + f + ["export"])
        return json.loads(output)

    def get_task_filter(self):
        config = os.path.expanduser("~/.taskui-filter")
        if not os.path.exists(config):
            return ["status:pending", "or", "start.not:"]
        with open(config, "rb") as f:
            return shlex.split(f.read().strip())

    def _on_timeout(self):
        gtk.timeout_add(FREQUENCY * 1000, self._on_timeout)
        if self.poll() and self.callback:
            self.callback(self.get_tasks())
