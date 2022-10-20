from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region, set_timeout

from functools import wraps
import iterm2

WINDOW_IDS = {}
TAB_IDS = {}
AUTO_FOCUS = False

def catch_exceptions(method):
    @wraps(method)
    async def wrapped(self, connection):
        try:
            return await method(self, connection)
        except Exception as e:
            print('ERROR in', self.__class__.__name__, e)
    return wrapped

class _TermCommand(WindowCommand):
    def run(self, **kwargs):
        self.vars = self.window.extract_variables()
        self.project = self.vars.get('project_base_name', 'default')
        self.initialize(**kwargs)
        iterm2.run_until_complete(self.coro)

    def initialize(self, **kwargs):
        pass

    @catch_exceptions
    async def coro(self, connection):
        ...


class TermListener(EventListener):
    def on_activated(self, view, **kwargs):
        print('on_activated')
        
    def on_pre_close_window(self, window, **kwargs):
        print('on_pre_close_window')

    def on_load_project(self, window, **kwargs):
        print('load and start')
        window.run_command('start_term')

    def on_pre_close_project(self, window, **kwargs):
        print('on_pre_close_project')

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
        await focus(connection, self.project, self.vars['file_name'])


class TermFocus(_TermCommand):
    @catch_exceptions
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)
        await focus(connection, self.project, self.vars['file_name'])


class StartTerm(_TermCommand):
    def initialize(self, ssh=None, **kwargs):
        tmux = '~/homebrew/bin/tmux'
        if ssh in ('g1', 'g2', 'scotty'):
            tmux = '~/bin/tmux'
        cmd = f'{tmux} -CC new-session -A -s {self.project}'
        if ssh:
            cmd = "ssh -t {} '{}'".format(ssh, cmd)
        self.cmd = cmd

    @catch_exceptions
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)
        # await app.async_activate()
        window = await iterm2.Window.async_create(connection, command=self.cmd)
        await window.async_set_variable('user.project', self.project)
        WINDOW_IDS[self.project] = window.window_id
        print('UPDATED WINDOW_IDS', WINDOW_IDS)


class StartRepl(_TermCommand):
    def initialize(self, **kwargs):
        self.file_path = self.vars['file_path']
        self.file = self.vars['file']
        file, extension = self.vars['file_name'], self.vars['file_extension']
        self.cmd = {
            'jl': '~/bin/jl',
            'r': 'radian',
            'rmd': 'radian',
            'py': 'ipython'
        }.get(extension.lower(), None)

    @catch_exceptions
    async def coro(self, connection):
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

        window_project = await window.async_get_variable('user.project')
        if window_project != self.project:
            print("BAD PROJECT WINDOW")
            return
        # we have to use a callback because async_create_tmux_tab doesn't work in sublime
        # and async_send_command doesn't wait for the tab to be initialized
        await tmux_conn.async_send_command(f'new-window "cd \'{self.file_path}\' && {self.cmd}; exec zsh"')
        set_timeout(lambda: iterm2.run_until_complete(self.update_tab), 1000)
    
    @catch_exceptions            
    async def update_tab(self, connection):
        app = await iterm2.async_get_app(connection)
        tab = app.current_terminal_window.current_tab
        TAB_IDS[self.file] = tab.tab_id
        await tab.async_set_title(self.vars['file_name'])
        await tab.current_session.async_set_variable('user.file', self.file)


class TermSendText(_TermCommand):
    def initialize(self, text, **kwargs):
        self.text = text + '\n'

    @catch_exceptions
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)        
        session = app.current_terminal_window.current_tab.current_session
        await session.async_send_text(self.text)


class LazyGit(_TermCommand):
    def initialize(self, **kwargs):
        self.folder = self.window.extract_variables()['folder']

    @catch_exceptions
    async def coro(self, connection):
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



async def get_window(app, project):
    try:
        return app.get_window_by_id(WINDOW_IDS[project])
    except KeyError:
        for window in app.windows:
            this_project = await window.async_get_variable('user.project')
            if this_project == project:
                WINDOW_IDS[project] = window.window_id
                return window
    raise Exception("Can't find window")

async def get_tab(app, file_name):
    try:
        return app.get_tab_by_id(TAB_IDS[file_name])
    except KeyError:
        for tab in app.current_window.tabs:
            # could try getting a more specific variable here
            title = await tab.async_get_variable('title')
            if title[2:] == file_name:
                TAB_IDS[file_name] = tab.tab_id
                return tab

async def focus(connection, project, file_name=None):
    app = await iterm2.async_get_app(connection)
    window = await get_window(app, project)
    await window.async_activate()

    if file_name is not None:
        tab = await get_tab(app, file_name)
        await tab.async_activate()