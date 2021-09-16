from sublime_plugin import WindowCommand
from sublime import Region

import sublime
import subprocess
import os
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
        tmux = 'tmux'
        if ssh in ('g1', 'g2', 'scotty'):
            tmux = '~/bin/tmux'
        cmd = '{} {} new-session -A -s {}'.format(tmux, CC, session)
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


class StartRepl(WindowCommand):
    def run(self, restart=False):
        vars = self.window.extract_variables()
        file, extension = vars['file_name'], vars['file_extension']
        cmd = {
            'jl': 'julia',
            'r': 'r',
            'rmd': 'r',
            'py': 'ipython'
        }.get(extension.lower(), None)

        def send(s):
                self.window.run_command("terminus_send_string", {"string": s})

        if restart:
            if cmd is not None:
                send("")
                send(cmd + '\n')
        else:
            send("c,")  # ctrl-t c ctrl-t ,
            send("" + file + "\n")  # cmd-backspace, then file name
            send("cd " + vars['file_path'] + "\n")


            if cmd is not None:
                send(cmd + '\n')

def find(view, sel, pattern, backward=False):
    if backward:
        regions = view.find_all(pattern)
        start = 0
        for i in range(len(regions)):
            if regions[i].end() >= sel.begin():
                if i == 0:
                    return Region(0, 0)
                else:
                    return regions[i-1]
        return regions[-1]
    else:
        return view.find(pattern, sel.end())


class JumpCell(WindowCommand):
    def run(self, backward=False):
        view = self.window.active_view()
        sels = view.sel()
        
        pattern = {
            'R Markdown': r'^```{r.*}\n',
            'LaTeX': r'^\\\w+section.*\n',
        }.get(view.syntax().name, r'^# %%.*\n')

        region = find(view, sels[0], pattern, backward)
        if region.a == -1:
            return
        
        sels.clear()
        sels.add(region.b)
        self.window.run_command("show_at_center")

        self.window.run_command("move", {
            "by": "characters", "forward": True
        })

        self.window.run_command("move", {
            "by": "characters", "forward": False
        })

        