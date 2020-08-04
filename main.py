from sublime_plugin import WindowCommand
import sublime
import subprocess

ITERM = os.path.join(os.path.dirname(__file__), "iterm.applescript")

def osascript(*args):
    subprocess.check_call(["osascript"] + list(args))


class SwitchTermPane(WindowCommand):
    def run(self, direction='right'):
        print('run SwitchTermPane')
        w = self.window
        g = w.active_group()
        sheets = w.sheets_in_group(1)
        active = w.active_sheet_in_group(1)
        i = next(i for i, s in enumerate(sheets) if s == active)
        print('active = ', i)
        offset = 1 if direction == 'right' else -1
        w.focus_sheet(sheets[(i + offset) % len(sheets)])
        w.focus_group(g)


class StartTerm(WindowCommand):
    def run(self, ssh=None, app='terminus', **kwargs):
        session = self.window.extract_variables().get("project_base_name", 'default')
        CC = '-CC' if app == 'iterm' else ''
        cmd = 'tmux {} new-session -A -s {}'.format(CC, session)
        if ssh:
            cmd = "ssh -t {} '{}'".format(ssh, cmd)

        if app == 'terminus':
            kwargs['shell_cmd'] = cmd
            self.window.run_command('terminus_open', kwargs)
            sublime.set_timeout_async(self.move_to_right)
        elif app == 'iterm':
            osascript(ITERM, cmd, "True")
            


    def move_to_right(self):
        view = self.window.active_view()
        if self.window.num_groups() == 1:
            self.window.run_command("create_pane", dict(direction="right"))
        self.window.set_view_index(view, 1, len(self.window.views_in_group(1)))
