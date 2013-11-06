#!/usr/bin/env python
# encoding=utf-8

from __future__ import print_function

import logging
import os
import shlex
import subprocess
import sys
import time


def log(message):
    print(message, file=sys.stderr)


def get_database_folder():
    p = subprocess.Popen(["task", "_show"],
        stdout=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode:
        raise RuntimeError("Could not read TaskWarrior config.")

    for line in out.split("\n"):
        if line.startswith("data.location="):
            return line.split("=", 1)[1]

    raise RuntimeException("Could not find database location.")


class Task(dict):
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
            return self.get_urgency()
        elif key == "tags":
            return self.get("tags", [])
        return super(Task, self).get(key, None)

    def get_urgency(self):
        # FIXME: implement the right algo.
        value = 0.0

        value += min((time.time() - int(self["entry"])) / 1000, 10)

        if "priority" in self:
            pri = {"L": 0, "M": 10, "H": 20}
            value += pri.get(self["priority"])

        return value

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

    def set_note(self, note):
        if not self.get("uuid"):
            raise RuntimeError("Cannot set a note for an unsaved task (no uuid).")

        if not isinstance(note, (str, unicode)):
            raise ValueError("Note must be a text string.")

        if note == self.get_note():
            return

        if isinstance(note, unicode):
            note = note.encode("utf-8")

        folder = os.path.join(os.path.dirname(
            get_database_folder()), "notes")
        if not os.path.exists(folder):
            os.makedirs(folder)
            log("Created folder {0}.".format(folder))

        fn = os.path.join(folder, self["uuid"])

        if note.strip():
            with open(fn, "wb") as f:
                f.write(note)
                log("Wrote a note to {0}".format(fn))
        elif os.path.exists(fn):
            os.unlink(fn)
            log("Deleted a note file {0}".format(fn))

    def get_note(self):
        if not self.get("uuid"):
            return None

        fn = os.path.join(os.path.dirname(
            get_database_folder()), "notes", self["uuid"])
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                return f.read().decode("utf-8")
        return u""


class Tasks(object):
    def __init__(self):
        self.tasks = []

        database_folder = get_database_folder()

        db = os.path.join(database_folder, "pending.data")
        self.tasks += self.load_data(db)

        db = os.path.join(database_folder, "completed.data")
        self.tasks += self.load_data(db)

    def load_data(self, database):
        """Reads the database file, parses it and returns a list of Task object
        instances, which contain all parsed data (values are unicode)."""
        if not os.path.exists(database):
            log("Database {0} does not exist.".format(database))
            return {}

        with open(database, "rb") as f:
            raw_data = f.read()

        tasks = []
        for line in raw_data.rstrip().split("\n"):
            if not line.startswith("[") or not line.endswith("]"):
                raise ValueError("Unsupported file format " \
                    "in {0}".format(database))

            task = Task()
            for kw in shlex.split(line[1:-1]):
                k, v = kw.split(":", 1)
                v = v.replace("\/", "/")  # FIXME: must be a better way
                v = v.decode("utf-8")
                if k == "tags":
                    v = v.split(",")
                task[k] = v

            tasks.append(task)

        return tasks

    def __iter__(self):
        return iter(self.tasks)

    def __getitem__(self, key):
        for task in self.tasks:
            if task["uuid"] == key:
                return task

    def __len__(self):
        return len(self.tasks)


if __name__ == "__main__":
    import sys
    uuids = sys.argv[1:]
    for task in Tasks():
        if uuids and task["uuid"] not in uuids:
            continue
        print(task)
        if "start" in task or task["uuid"] in uuids:
            for k, v in sorted(task.items()):
                print("  {0}: {1}".format(k, unicode(v).encode("utf-8")))


__all__ = ["Task", "Tasks"]
