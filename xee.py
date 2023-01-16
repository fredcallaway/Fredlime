from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region, set_timeout, set_timeout_async

import os
import re
import subprocess
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCHERS = {}

class BackgroundOpenNew(FileSystemEventHandler):
    """Opens newly created images"""
    def __init__(self, delay):
        self.delay = delay
        self.last = None
        super().__init__()


    def on_created(self, event):
        if self.last != event.src_path:
            self.last = event.src_path
            os.system(f'sleep {self.delay}; open -g "{event.src_path}"')

class Watcher(object):
    """Opens newly created files."""
    def __init__(self, path, delay):
        super().__init__()
        self.path = path
        self.observer = Observer()
        self.observer.schedule(BackgroundOpenNew(delay), self.path, recursive=True)
        self.start()

    def start(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()

class WatchFigs(WindowCommand):
    def run(self, action='start', **kwargs):
        folder = self.window.extract_variables().get('folder')
        if folder is None:
            return

        if action == 'start':
            set_timeout_async(lambda: start_watch(folder))

        elif action == 'stop':
            set_timeout_async(lambda: stop_watch(folder))

def start_watch(folder):
    path = f"{folder}/.fighist"
    os.system(f'open -ga "Xee³" "{path}"')
    if folder not in WATCHERS:
        print('[WatchFigs] watching', path)
        WATCHERS[folder] = Watcher(path, 0.1)

def stop_watch(folder):
    if folder in WATCHERS:
        watcher = WATCHERS.pop(folder)
        watcher.stop()
        print("[WatchFigs] stopped")


class FigsListener(EventListener):
    def on_activated_async(self, view, **kwargs):
        folder = view.window().extract_variables().get('folder')
        if folder in WATCHERS and view.syntax().name != 'MultiMarkdown':
            path = f"{folder}/.fighist"
            os.system(f'open -ga "Xee³" "{path}"')


    # def on_pre_close_window(self, window, **kwargs):
        # logging.info('on_pre_close_window')

    # def on_load_project(self, window, **kwargs):
        # logging.info('load and start')
        # window.run_command('start_term')

    def on_pre_close_project(self, window, **kwargs):
        folder = window.extract_variables().get('folder')
        set_timeout_async(lambda: stop_watch(folder))
