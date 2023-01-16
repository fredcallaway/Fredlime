from sublime_plugin import WindowCommand, TextCommand
from sublime import Region

import sublime
import subprocess
import os
import random

class PreviewFile(WindowCommand):
    def run(self, **kwargs):
        # print("PreviewFile", kwargs.get("file", 'NO FILE'))
        self.window.open_file(kwargs["file"], sublime.ENCODED_POSITION | sublime.TRANSIENT)