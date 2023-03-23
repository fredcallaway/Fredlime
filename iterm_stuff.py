from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region, set_timeout, set_timeout_async

import os
import re
from functools import wraps
import traceback
import asyncio
import json

AUTO_FOCUS_TAB = True
AUTO_FOCUS_WINDOW = True

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/tmp/iterm.log"),
        logging.StreamHandler()
    ]
)

FIFO_PATH = "/tmp/iterm_fifo"
if not os.path.exists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

def send_message(command, vars, kws):
    msg = json.dumps({
        'command': command,
        'vars': vars,
        'kws': kws
    })
    try:
        out = os.open(FIFO_PATH, os.O_NONBLOCK | os.O_WRONLY)
    except OSError as e:
        print("Could not open FIFO.", e)
    else:
        os.write(out, bytes(msg, 'utf-8'))
        os.close(out)
        # print("Sent message:", msg)

# %% ==================== commands ====================

class _TermCommand(WindowCommand):
    def send_message(self, **kwargs):
        command = self.__class__.__name__
        logging.debug(command, **kwargs)
        send_message(command, vars=self.window.extract_variables(), kws=kwargs)

    def run(self, **kwargs):
        self.send_message(**kwargs)

class TermFocus(_TermCommand):
    def run(self, **kwargs):
        if AUTO_FOCUS_WINDOW:
            self.send_message(focus_tab=AUTO_FOCUS_TAB)

class StartTerm(_TermCommand):
    pass

class CloseTerm(_TermCommand):
    pass

class StartRepl(_TermCommand):
    pass

class TermSendText(_TermCommand):
    pass

class LazyGit(_TermCommand):
    pass

# %% ==================== listener ====================

class TermListener(EventListener):
    def on_activated_async(self, view, **kwargs):
        if AUTO_FOCUS_WINDOW:
            if view.syntax().name == 'MultiMarkdown':
                pass
                # file = view.window().extract_variables().get('file')
                # os.system(f'open -ga "Marked 2" "{file}"')
            else:
                view.window().run_command('term_focus')

    # def on_pre_close_window(self, window, **kwargs):
        # logging.info('on_pre_close_window')
        
    # def on_load_project(self, window, **kwargs):
        # logging.info('load and start')
        # window.run_command('start_term')

    def on_pre_close_project(self, window, **kwargs):
        logging.info('on_pre_close_project')
        window.run_command('close_term')


class TermToggleAutoFocus(WindowCommand):
    def run(self, which='tab', **kwargs):
        if which == 'window':
            global AUTO_FOCUS_WINDOW
            AUTO_FOCUS_WINDOW = not AUTO_FOCUS_WINDOW
            logging.info(f'AUTO_FOCUS_WINDOW = {AUTO_FOCUS_WINDOW}')
            if AUTO_FOCUS_WINDOW:
                self.window.run_command('term_focus')
        else:
            global AUTO_FOCUS_TAB
            AUTO_FOCUS_TAB = not AUTO_FOCUS_TAB
            logging.info(f'AUTO_FOCUS_TAB = {AUTO_FOCUS_TAB}')
            if AUTO_FOCUS_TAB:
                self.window.run_command('term_focus')
