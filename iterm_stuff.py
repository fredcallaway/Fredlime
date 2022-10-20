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
        self.ssh = ssh

    @catch_exceptions
    async def coro(self, connection):
        await create_window(connection, self.project)


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
        # self.timeouts = 0

    @catch_exceptions
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)
        window = await get_window(app, self.project)
        if window is None:
            return
            # if self.timeouts == 0:
            #     await create_window(connection, self.project)
            # elif self.timeouts <= 5:
            #     self.timeouts += 1
            #     timeout(lambda: iterm2.run_until_complete(self.coro), 1000)
            # else:
            #     raise Exception("Too many timeouts")
            # return

        # this should never happen, could delete
        window_project = await window.async_get_variable('user.project')
        if window_project != self.project:
            raise Exception("BAD PROJECT WINDOW")

        tmux = await get_tmux(connection, self.project)
        await tmux.async_send_command(f'new-window "cd \'{self.file_path}\' && {self.cmd}; exec zsh"')
        # we have to use a callback because async_create_tmux_tab doesn't work in sublime
        # and async_send_command doesn't wait for the tab to be initialized
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


async def create_window(connection, project, ssh=None):
    tmux = '~/homebrew/bin/tmux'
    if ssh in ('g1', 'g2', 'scotty'):
        tmux = '~/bin/tmux'
    cmd = f'{tmux} -CC new-session -A -s {project}'
    if ssh:
        cmd = f"ssh -t {ssh} '{cmd}'"

    app = await iterm2.async_get_app(connection)
    window = await iterm2.Window.async_create(connection, command=cmd)
    await window.async_set_variable('user.project', project)
    WINDOW_IDS[project] = window.window_id
    return window

async def get_window(app, project):
    try:
        return app.get_window_by_id(WINDOW_IDS[project])
    except KeyError:
        for window in app.windows:
            this_project = await window.async_get_variable('user.project')
            if this_project == project:
                WINDOW_IDS[project] = window.window_id
                return window

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

async def get_tmux(connection, project):
    # get tmux connection
    tmux_conns = await iterm2.async_get_tmux_connections(connection)
    for tmux_conn in tmux_conns:
        tmux_session = tmux_conn.owning_session.name.split(' ')[-1][:-1]
        if tmux_session == project:
            return tmux_conn
    
    raise Exception("Could not find tmux connection")

async def focus(connection, project, file_name=None):
    app = await iterm2.async_get_app(connection)
    window = await get_window(app, project)
    await window.async_activate()

    if file_name is not None:
        tab = await get_tab(app, file_name)
        await tab.async_activate()