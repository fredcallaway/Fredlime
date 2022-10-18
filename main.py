from sublime_plugin import WindowCommand, TextCommand
from sublime import Region

import sublime
import subprocess
import os

def here(path):
    return os.path.join(os.path.dirname(__file__), path)

ITERM = here("iterm.applescript")

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
        tmux = '~/homebrew/bin/tmux'
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

class LazyGit(WindowCommand):
    def run(self, ssh=None, app='iterm', **kwargs):
        folder = self.window.extract_variables()['folder']
        # session = self.window.extract_variables().get("project_base_name", 'default')
        # CC = '-CC' if app == 'iterm' else ''
        # tmux = 'tmux'
        # if ssh in ('g1', 'g2', 'scotty'):
            # tmux = '~/bin/tmux'
        # cmd = 'cd {} && /Users/fredcallaway/bin/lazygit'.format(folder)
        subprocess.check_call([here('lazygit.py'), folder])

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


def find_surround(view, sel, pattern):
    regions = view.find_all(pattern)
    start = 0
    for i in range(len(regions)):
        end = regions[i].begin()
        if start <= sel.begin() and end >= sel.end():
            break
        start = regions[i].begin()
    else:  # no pattern occurrence after sel, go to end of file
        end = view.size()
    # if start > 0:
    #     start = view.find('\n+', start).end()        
    return sublime.Region(start, end)


class JumpCell(TextCommand):
    def run(self, edit, backward=False):
        view = self.view
        sels = view.sel()
        
        pattern = {
            'R Markdown': r'^```{r.*}\n',
            'LaTeX': r'^\\(\w*section|paragraph).*\n',
        }.get(view.syntax().name, r'^# %%.*\n')

        region = find(view, sels[0], pattern, backward)
        if region.a == -1:
            return
        
        sels.clear()
        sels.add(region.b)
        view.show(region)

class SelectCell(TextCommand):
    def run(self, edit):
        print("running select_cell")
        view = self.view
        sels = view.sel()

        pattern = {
            'R Markdown': r'^```{r.*}\n',
            'LaTeX': r'^\\(\w*section|paragraph).*\n',
        }.get(view.syntax().name, r'^# %%.*\n')
        s = find_surround(view, sels[0], pattern)

        print(s)
        # start = self.view.find('\n', s.begin()).begin()+1
        start = s.begin()
        # print('line', self.view.substr(self.view.line(start)))
        # print('||', self.view.substr(sublime.Region(start, s.end()-1)), '||', sep='')
        sels.clear()
        new = sublime.Region(start, s.end())
        sels.add(new)
        view.show(new)



class FoldCell(TextCommand):
    def run(self, edit):
        view = self.view
        view.run_command("select_cell")
        view.run_command("move", {"by": "characters", "forward": False, "extend":True})
        view.run_command("reverse_select")
        view.run_command("move", {"by": "lines", "forward": True, "extend":True})
        view.run_command("fold")


