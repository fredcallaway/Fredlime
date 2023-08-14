import sublime, sublime_plugin
import subprocess


class InsertFilePath(sublime_plugin.TextCommand):

    def run(self, edit):
        # self.window.show_input_panel("Goto Line:", "", self.on_done, None, None)
        self.window = self.view.window()
        v = self.window.extract_variables()
        folder = v.get('folder', v.get('file_path'))
        if folder is None:
            print("No folder!")
            return

        fd = 'fd --exclude .git --exclude .cache --no-ignore-vcs --follow'.split(' ')
        files = subprocess.check_output([*fd, ".", folder]).decode().strip().split('\n')
        self.files = [f.replace(folder + '/', '') for f in files]
        self.window.show_quick_panel(self.files, self.on_select)

        selected_text = self.view.substr(self.view.sel()[0])
        print('selected_text', selected_text)
        self.window.run_command("append", { "characters": selected_text})
        self.window.run_command("move_to", {"to": "eol"})

    def on_select(self, i):
        self.view.run_command("insert", {"characters": self.files[i]})


    def on_done(self, text):
        print('Done!', text)
        try:
            line = int(text)
            if self.window.active_view():
                self.window.active_view().run_command("goto_line", {"line": line} )
        except ValueError:
            pass
