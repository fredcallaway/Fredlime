from sublime_plugin import WindowCommand, TextCommand
from sublime import Region

import sublime
import subprocess
import os

def find(view, sel, pattern, backward=False, include_current=False):
    offset = 1 if include_current else 0
    if backward:
        regions = view.find_all(pattern)
        start = 0
        for i in range(len(regions)):
            if regions[i].end() >= sel.begin() + offset:
                if i == 0:
                    return Region(0, 0)
                else:
                    return regions[i-1]
        return regions[-1]
    else:
        return view.find(pattern, sel.end())


def find_surround(view, sel, pattern):
    if not isinstance(pattern, tuple):
        pattern = (pattern, pattern)
        end_offset = -1
    else:
        end_offset = 0

    start_pat, end_pat = pattern

    start = find(view, sel, start_pat, backward=True, include_current=True).begin()
    end = find(view, sel, end_pat, backward=False).begin()
    if end == -1:
        end = view.size()

    return sublime.Region(start, end + end_offset)


class JumpCell(TextCommand):
    def run(self, edit, backward=False):
        view = self.view
        sels = view.sel()

        pattern = {
            'R Markdown': r'^```{r.*}\n',
            'LaTeX': r'^\\(\w*section|paragraph).*\n',
            'JSON': 'indent',
            'JavaScript': 'indent'
        }.get(view.syntax().name, r'^# %%.*\n')

        if pattern == 'indent':
            line = view.line(view.sel()[0].begin())
            this_indent = len(view.substr(line)) - len(view.substr(line).lstrip(' '))
            print(this_indent)
            pattern = '\n' + this_indent * ' ' + r'(?=[^\s])'
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
            'R Markdown': (r'^```{r.*}\n', r'(?<=^```)\n'),
            'LaTeX': r'^\\(\w*section|paragraph).*\n',
        }.get(view.syntax().name, r'# %%.*\n')
        new = find_surround(view, sels[0], pattern)
        sels.clear()
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
