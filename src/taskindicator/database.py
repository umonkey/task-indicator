import os

if os.getenv("TASK_INDICATOR") == "sqlite":
    from database_sqlite import Database
else:
    from database_tw import Database
