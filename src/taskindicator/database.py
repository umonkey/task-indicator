# encoding=utf-8

import gtk
import os
import shlex

from taskindicator import util


FREQUENCY = 1


class Database(object):
    def __init__(self, callback=None):
        self.filename = self.get_filename()
        self.mtime = None
        self._tasks = None

        self.callback = callback

    def modified_since(self, ts):
        return os.stat(self.filename).st_mtime > ts

    def get_filename(self):
        for line in util.run_command(["task", "_show"]).split("\n"):
            if line.startswith("data.location="):
                folder = line.split("=", 1)[1].strip()
                return os.path.join(folder, "pending.data")
        raise RuntimeError("Could not find task database location.")

    def get_tasks(self):
        if self._tasks is None:
            util.log("Reloading tasks.")
            self._tasks = self.load_tasks()
        return self._tasks

    def refresh(self):
        self._tasks = None
        return self.get_tasks()

    def load_tasks(self):
        from taskw import Tasks
        # f = self.get_task_filter()
        return Tasks()

    def get_task_filter(self):
        config = os.path.expanduser("~/.taskui-filter")
        if not os.path.exists(config):
            return ["status:pending", "or", "start.not:"]
        with open(config, "rb") as f:
            return shlex.split(f.read().strip())

    def get_task_info(self, task_id):
        from taskw import Tasks
        return Tasks()[task_id]

    def start_task(self, task_id):
        util.log("Starting task {0}.", task_id)
        util.run_command(["task", task_id, "start"])

    def stop_task(self, task_id):
        util.log("Stopping task {0}.", task_id)
        util.run_command(["task", task_id, "stop"])

    def finish_task(self, task_id):
        util.log("Finishing task {0}.", task_id)
        util.run_command(["task", task_id, "stop"])
        util.run_command(["task", task_id, "done"])

    def restart_task(self, task_id):
        util.log("Restarting task {0}.", task_id)
        util.run_command(["task", task_id, "mod", "status:pending"])
        util.run_command(["task", task_id, "start"])
