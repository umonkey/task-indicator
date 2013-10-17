#!/usr/bin/env python
# encoding=utf-8

from __future__ import print_function

import logging
import os
import shlex
import time


logger = logging.getLogger("taskw.py")


class Task(dict):
    def __init__(self, database):
        self.database = database

    def __repr__(self):
        s = "<Task {0}".format(self["uuid"][:8])
        s += ", status={0}".format(self["status"])
        if "project" in self:
            # FIXME: test with unicode names
            s += ", pro:{0}".format(self["project"])
        if "priority" in self:
            s += ", pri:{0}".format(self["priority"])
        if "start" in self:
            s += ", dur:{0}".format(self.format_current_runtime())
        s += ">"
        return s

    def __getitem__(self, key):
        if key == "urgency":
            return "0"
        return super(Task, self).get(key, None)

    def get_current_runtime(self):
        if not self.get("start"):
            return 0

        start = int(self["start"])
        duration = time.time() - start
        return int(duration)

    def format_current_runtime(self):
        duration = self.get_current_runtime()

        seconds = duration % 60
        minutes = (duration / 60) % 60
        hours = (duration / 3600) % 60

        return "%u:%02u:%02u" % (hours, minutes, seconds)


class Tasks(object):
    def __init__(self, database=None):
        if database is None:
            database = os.path.expanduser("~/.task/pending.data")
        self.database = database

        self.pending = self.load_data()

    def load_data(self):
        """Reads the database file, parses it and returns a list of Task object
        instances, which contain all parsed data (values are unicode)."""
        if not os.path.exists(self.database):
            logger.warning("Database {0} does not exist.".format(self.database))
            return {}

        with open(self.database, "rb") as f:
            raw_data = f.read()

        tasks = []
        for line in raw_data.rstrip().split("\n"):
            if not line.startswith("[") or not line.endswith("]"):
                raise ValueError("Unsupported file format " \
                    "in {0}".format(filename))

            task = Task(self.database)
            for kw in shlex.split(line[1:-1]):
                k, v = kw.split(":", 1)
                task[k] = v.decode("utf-8")

            tasks.append(task)

        return tasks

    def __iter__(self):
        return iter(self.pending)

    def __getitem__(self, key):
        for task in self.pending:
            if task["uuid"] == key:
                return task

    def __len__(self):
        return len(self.pending)


if __name__ == "__main__":
    for task in Tasks():
        print(task)
