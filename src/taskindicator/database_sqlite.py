# vim: set fileencoding=utf-8 tw=0:

import os
import time

import sqlite3

from taskindicator import util


DATABASE_PATH = "~/.task/tasks.sqlite"

# TODO: foreign key.
DATABASE_INIT = """
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  created INTEGER UNSIGNED NOT NULL,
  modified INTEGER UNSIGNED NOT NULL,
  project VARCHAR(255) NULL,
  summary VARCHAR(255) NULL,
  priority INT NOT NULL DEFAULT 0,
  status VARCHAR(255) NOT NULL,  -- deleted, pending, started, completed
  description TEXT
);

CREATE TABLE IF NOT EXISTS changes (
  id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER UNSIGNED NOT NULL,
  ts INTEGER UNSIGNED NOT NULL,
  status VARCHAR(255) NOT NULL,
  duration INTEGER UNSIGNED NULL
);
"""


class Task(dict):
    def __getitem__(self, k):
        if k == "urgency":
            return 1
        return super(Task, self).__getitem__(k)

    @classmethod
    def from_row(cls, row, db):
        t = cls(row)
        t.db = db
        return t

    def id(self):
        return self.get("id")

    def get_summary(self):
        return self["summary"]

    def get_project(self):
        return self["project"]

    def get_description(self):
        return self["description"]

    def set_note(self, note):
        self["description"] = note

    def is_started(self):
        return self["status"] == "started"

    is_active = is_started

    def set_active(self, active=True):
        self["status"] = "started" if active else "pending"

    def get_start_ts(self):
        last = self.db.get_last_change(self.id())
        if last and last["status"] == "started":
            return int(last["ts"])

    def is_closed(self):
        return self["status"] in ("deleted", "completed")

    def is_deleted(self):
        return self["status"] == "deleted"


class Database(object):
    def __init__(self):
        self.filename = os.path.expanduser(DATABASE_PATH)
        self.conn = self.connect(self.filename)

    def connect(self, filename):
        conn = sqlite3.connect(filename)
        conn.text_factory = str
        conn.cursor().executescript(DATABASE_INIT)
        conn.commit()
        return conn

    def modified_since(self, ts):
        return os.stat(self.filename).st_mtime > ts

    def refresh(self):
        pass

    def get_tasks(self):
        """
        Returns a list of task objects.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT id, created, modified, project, summary, status, priority, description FROM tasks")
        rows = cur.fetchall()

        header = ["id", "created", "modified", "project", "summary", "status", "priority", "description"]
        return [Task.from_row(zip(header, row), self) for row in rows]

    def add_task(self, data):
        ts = int(time.time())

        params = {"created": ts,
                  "modified": ts,
                  "project": None,
                  "summary": "Untitled task",
                  "priority": 0,
                  "status": "pending",
                  "description": None,
                  }
        params.update(data)

        cur = self.conn.cursor()

        cur.execute("INSERT INTO tasks (created, modified, project, summary, priority, status, description) VALUES (?, ?, ?, ?, ?, ?, ?)", (params["created"], params["modified"], params["project"], params["summary"], params["priority"], params["status"], params["description"]))
        task_id = cur.lastrowid

        cur.execute("INSERT INTO changes (task_id, ts, status, duration) VALUES (?, ?, ?, ?)", (task_id, ts, params["status"], 0))

        self.conn.commit()

    def update_task(self, task_id, properties):
        ts = int(time.time())

        # Use fresh data for missing fields, to prevent status changes etc.
        params = self.get_task_info(task_id)
        params.update(properties)
        params["modified"] = ts

        util.log("Task update: {0}", params)

        cur = self.conn.cursor()

        cur.execute("UPDATE tasks SET modified = ?, project = ?, summary = ?, priority = ?, status = ?, description = ? WHERE id = ?", (params["modified"], params["project"], params["summary"], params["priority"], params["status"], params["description"], task_id))

        cur.execute("INSERT INTO changes (task_id, ts, status, duration) VALUES (?, ?, ?, ?)", (task_id, ts, params["status"], 0))

        self.conn.commit()

    def get_projects(self):
        projects = {}
        for task in self.get_tasks():
            projects[task.get_project()] = True
        return projects.keys()

    def get_task_info(self, task_id):
        cur = self.conn.cursor()

        cur.execute("SELECT id, created, modified, project, summary, status, priority, description FROM tasks WHERE id = ?", (task_id, ))
        rows = cur.fetchall()

        header = ["id", "created", "modified", "project", "summary", "status", "priority", "description"]
        task = Task.from_row(zip(header, rows[0]), self)
        #print(task)
        return task

    def start_task(self, task_id):
        self.set_task_status(task_id, "started")

    def stop_task(self, task_id):
        self.set_task_status(task_id, "pending")

    def finish_task(self, task_id):
        self.set_task_status(task_id, "completed")

    def restart_task(self, task_id):
        self.set_task_status(task_id, "started")

    def set_task_status(self, task_id, status):
        util.log("Changing status of task {0} to {1}.", task_id, status)

        cur = self.conn.cursor()
        ts = int(time.time())

        last = self.get_last_change(task_id)
        if last is not None:
            if status == last["status"]:
                return  # no changes
            duration = ts - int(last["ts"])
            cur.execute("UPDATE changes SET duration = ? WHERE id = ?", (duration, last["id"]))

        cur.execute("UPDATE tasks SET modified = ?, status = ? WHERE id = ?", (ts, status, task_id))
        cur.execute("INSERT INTO changes (task_id, ts, status) VALUES (?, ?, ?)", (task_id, ts, status))
        self.conn.commit()

    def get_last_change(self, task_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, ts, status, duration FROM changes WHERE task_id = ? ORDER BY id DESC LIMIT 1", (task_id, ))
        row = cur.fetchone()
        if row is not None:
            return dict(zip(("id", "ts", "status", "duration"), row))
