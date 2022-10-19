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


