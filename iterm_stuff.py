from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region, set_timeout

import platform
import iterm2
import re
import time

WINDOW_IDS = {}
TAB_IDS = {}
AUTO_FOCUS = False

class TermToggleAutoFocus(WindowCommand):
    def run(self, **kwargs):
        global AUTO_FOCUS
        AUTO_FOCUS = not AUTO_FOCUS
        if AUTO_FOCUS:
            self.window.run_command('term_focus')

class FocusListener(EventListener):
    """docstring for FocusListener"""
    def on_activated(self, view, **kwargs):
        if AUTO_FOCUS:
            self.vars = view.window().extract_variables()
            self.project = self.vars.get('project_base_name', 'default')
            iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        await focus(self, connection)

class TermFocus(WindowCommand):
    def run(self, **kwargs):
        self.vars = self.window.extract_variables()
        self.project = self.vars.get('project_base_name', 'default')
        iterm2.run_until_complete(self.coro)


    async def coro(self, connection):
        await focus(self, connection)

async def focus(self, connection):
    try:
        app = await iterm2.async_get_app(connection)
        if self.project not in WINDOW_IDS:
            for window in app.windows:
                # print(window.async_get_variable('user.project') == 'recstrats')
                project = await window.async_get_variable('user.project')
                WINDOW_IDS[project] = window.window_id
                if project == self.project:
                    break
            else:
                print("CANNOT FIND WINDOW")
                return

        window = app.get_window_by_id(WINDOW_IDS[self.project])
        await window.async_activate()

        if self.vars['file'] in TAB_IDS:
            await app.get_tab_by_id(TAB_IDS[self.vars['file']]).async_activate()
            return

        # couldn't find tab
        window = app.current_window
        for tab in window.tabs:
            title = await tab.async_get_variable('title')
            if title[2:] == self.vars['file_name']:
                await tab.async_activate()
                TAB_IDS[self.vars['file']] = tab.tab_id
                return
    except BaseException as e:
        print('ERROR TermFocus', e)



class TermCommand(WindowCommand):
    def run(self, **kwargs):
        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        try:
            app = await iterm2.async_get_app(connection)        
            await app.async_activate()
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)

class StartRepl(WindowCommand):
    def run(self, restart=False):
        self.vars = self.window.extract_variables()
        self.project = self.vars.get('project_base_name', 'default')
        self.file_path = self.vars['file_path']
        self.file = self.vars['file']
        file, extension = self.vars['file_name'], self.vars['file_extension']
        self. cmd = {
            'jl': 'jl',
            'r': 'r',
            'rmd': 'r',
            'py': 'ipython'
        }.get(extension.lower(), None)

        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        try:
            app = await iterm2.async_get_app(connection)
            window = app.current_terminal_window
            if not window:
                print('NO WINDOW')
                return
            
            # get tmux connection
            tmux_conns = await iterm2.async_get_tmux_connections(connection)
            for tmux_conn in tmux_conns:
                project = tmux_conn.owning_session.name.split(' ')[-1][:-1]
                if project == self.project:
                    print('found')
                    break
            else:
                print('not found')
                return

            # TODO we need to make sure we're using the right tmux conn
            # window = app.current_window
            window_project = await window.async_get_variable('user.project')
            if window_project != self.project:
                print("BAD PROJECT WINDOW")
                return
            # we have to use a callback because async_create_tmux_tab doesn't work in sublime
            # and async_send_command doesn't wait for the tab to be initialized
            await tmux_conn.async_send_command(f'new-window "cd \'{self.file_path}\' && {self.cmd}; exec zsh"')
            set_timeout(lambda: iterm2.run_until_complete(self.update_tab), 1000)
            
        except BaseException as e:
            print('ERROR in', self.__class__.__name__, e)

    async def update_tab(self, connection):
        try:
            app = await iterm2.async_get_app(connection)
            tab = app.current_terminal_window.current_tab
            TAB_IDS[self.file] = tab.tab_id
            await tab.async_set_title(self.vars['file_name'])
            await tab.current_session.async_set_variable('user.file', self.file)

        except BaseException as e:
            print('ERROR in update_tab of', self.__class__.__name__, e)

class StartTerm(WindowCommand):
    def run(self, ssh=None, **kwargs):
        self.project = self.window.extract_variables().get("project_base_name", 'default')
        tmux = '~/homebrew/bin/tmux'
        if ssh in ('g1', 'g2', 'scotty'):
            tmux = '~/bin/tmux'
        cmd = f'{tmux} -CC new-session -A -s {self.project}'
        if ssh:
            cmd = "ssh -t {} '{}'".format(ssh, cmd)
        self.cmd = cmd

        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        try:
            app = await iterm2.async_get_app(connection)
            await app.async_activate()
            window = await iterm2.Window.async_create(connection, command=self.cmd)
            await window.async_set_variable('user.project', self.project)
            WINDOW_IDS[self.project] = window.window_id
            print('UPDATED WINDOW_IDS', WINDOW_IDS)
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)



class TermSendText(WindowCommand):
    def run(self, text, **kwargs):
        self.text = text + '\n'
        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        try:
            app = await iterm2.async_get_app(connection)        
            session = app.current_terminal_window.current_tab.current_session
            await session.async_send_text(self.text)
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)


class LazyGit(WindowCommand):
    def run(self, **kwargs):
        self.folder = self.window.extract_variables()['folder']
        # subprocess.check_call([here('lazygit.py'), self.folder])
        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
        try:
            app = await iterm2.async_get_app(connection)        
            await app.async_activate()

            # check if already exists and activate
            for window in app.windows:
                for tab in window.tabs:
                    for session in tab.sessions:
                        folder = await session.async_get_variable("user.lazygit-folder")
                        if folder == self.folder:
                            await session.async_activate()
                            return

            # self.folder = '/Users/fredcallaway/projects/recstrats'

            # Start in a new tab or window
            cmd = f"zsh -dfic 'cd \"{self.folder}\" && /Users/fredcallaway/bin/lazygit'"
            window = app.current_terminal_window
            if not window:
                window = await iterm2.Window.async_create(connection, command=cmd)
            else:
                tab = await window.async_create_tab(command=cmd)

            session = window.current_tab.current_session
            await session.async_set_variable("user.lazygit-folder", self.folder)
            await window.async_activate()
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)


async def test(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_terminal_window.tabs[0].sessions[0]
    await session.async_send_text('x = 1\n')

