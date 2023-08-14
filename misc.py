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


class NewJuliaScript(WindowCommand):
    def run(self):
        self.window.show_input_panel("Script Name", "", self.create, None, None)

    def create(self, name):
        self.window.open_file(f"{name}.jl")
        folder = self.window.extract_variables()['folder']
        main = os.path.join(folder, "main.jl")
        with open(main, "a") as f:
            f.write(f'include("{name}.jl")\n')
