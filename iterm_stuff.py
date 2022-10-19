from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region

import platform
import iterm2
import re

WINDOW_IDS = {}

class FocusListener(EventListener):
    """docstring for FocusListener"""
    def on_activated(self, view, **kwargs):
        self.vars = view.window().extract_variables()
        self.project = self.vars.get('project_base_name', 'default')

        file = self.vars['file']
        print('new focus', file, WINDOW_IDS)
        # return

        iterm2.run_until_complete(self.coro)

    async def coro(self, connection):
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
            print("FOUND WINDOW!")
            
            await window.async_activate()

            # tmux_conns = await iterm2.async_get_tmux_connections(connection)
            # for tc in tmux_conns:
            #     project = tc.owning_session.name.split(' ')[-1][:-1]
            #     if project == self.project:
            #         app.windows
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)



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
            print('>>>>>> begin coro')
            app = await iterm2.async_get_app(connection)
            # await app.async_activate()
            window = app.current_terminal_window
            if not window:
                print('NO WINDOW')
                return
                # window = await iterm2.Window.async_create(connection, command=cmd)
            
            tmux_conns = await iterm2.async_get_tmux_connections(connection)

            project = self.vars.get('project_base_name', 'default')

            # TODO we need to make sure we're using the right tmux conn
            return

            if tmux_conns:
                tmux_conn = tmux_conns[0]
                tab = await window.async_create_tmux_tab(tmux_conn)
            else:
                tab = await window.async_create_tab()

            try:
                print(self.vars['file_path'])
            except:
                print('cannot print vars')
            print(self.vars['file_path'])
            file_path = self.vars['file_path']
            # await tab.current_session.async_send_text(f'echo 1')
            await tab.current_session.async_send_text(f'cd "{file_path}" && {self.cmd}\n')
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)

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

