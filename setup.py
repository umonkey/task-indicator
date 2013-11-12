#!/usr/bin/env python
# vim: set fileencoding=utf-8:

from distutils.core import setup


classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: Unix',
    'Programming Language :: Python',
    'Topic :: Office/Business :: Scheduling',
    'Topic :: Software Development :: Bug Tracking',
    ]

longdesc = """A simple indicator application that helps do simple things with
TaskWarrior, like finding and adding tasks, starting and stopping them, track
current activity time, etc.  Supports task notes.

For more complex operations CLI must be used.

Indicator applet and menu screenshot:

.. image:: http://umonkey.net/projects/task-indicator/menu.png

Task editor:

.. image:: http://umonkey.net/projects/task-indicator/info.png

Search dialog:

.. image:: http://umonkey.net/projects/task-indicator/search.png
"""

data_files = [
    ("share/icons/hicolor/scalable/apps", ["icons/hicolor/scalable/apps/taskui.svg", "icons/hicolor/scalable/apps/taskui-active.svg"]),
    ("share/applications", ["data/TaskIndicator.desktop"]),
]

setup(
    author = 'Justin Forest',
    author_email = 'hex@umonkey.net',
    classifiers = classifiers,
    data_files = data_files,
    description = 'TaskWarrior indicator applet',
    long_description = longdesc,
    license = 'MIT',
    name = 'task-indicator',
    package_dir = {'': 'src'},
    packages = ['taskindicator'],
    requires = ['gtk', 'json', 'dateutil'],
    scripts = ['task-indicator'],
    url = 'http://umonkey.net/task-indicator/en/',
    download_url = 'http://code.umonkey.net/task-indicator/archive/default.zip',
    version = '1.15'
)
