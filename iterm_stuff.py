from sublime_plugin import EventListener, WindowCommand, TextCommand
from sublime import Region, set_timeout, set_timeout_async

from functools import wraps
import traceback

import iterm2

WINDOW_IDS = {}
TAB_IDS = {}
AUTO_FOCUS_TAB = False
AUTO_FOCUS_WINDOW = True

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/tmp/iterm.log"),
        logging.StreamHandler()
    ]
)

def safe(func):
    @wraps(func)
    async def wrapped(*args):
        try:
            return await func(*args)
        except Exception as e:
            logging.exception(f'in {func}')
            
    return wrapped

class _TermCommand(WindowCommand):
    def run(self, **kwargs):
        self.vars = self.window.extract_variables()
        self.project = self.vars.get('project_base_name', 'default')
        self.initialize(**kwargs)
        set_timeout_async(lambda: iterm2.run_until_complete(self.coro))

    def initialize(self, **kwargs):
        pass

    @safe
    async def coro(self, connection):
        ...


class TermListener(EventListener):
    def on_activated(self, view, **kwargs):
        if AUTO_FOCUS_WINDOW:
            view.window().run_command('term_focus')

    # def on_pre_close_window(self, window, **kwargs):
        # logging.info('on_pre_close_window')
        
    def on_load_project(self, window, **kwargs):
        logging.info('load and start')
        window.run_command('start_term')

    def on_pre_close_project(self, window, **kwargs):
        logging.info('on_pre_close_project')
        # window.run_command('close_term')


class TermToggleAutoFocus(WindowCommand):
    def run(self, **kwargs):
        global AUTO_FOCUS_TAB
        AUTO_FOCUS_TAB = not AUTO_FOCUS_TAB
        logging.info(f'AUTO_FOCUS_TAB = {AUTO_FOCUS_TAB}')
        if AUTO_FOCUS_TAB:
            self.window.run_command('term_focus')


class TermFocus(_TermCommand):
    @safe
    async def coro(self, connection):
        logging.info('TermFocus')
        app = await iterm2.async_get_app(connection)
        file_name = self.vars.get('file_name', None) if AUTO_FOCUS_TAB else None
        await focus(connection, self.project, file_name)


class TestTerm(WindowCommand):
    def run(self, **kwargs):
        self.vars = self.window.extract_variables()
        self.project = self.vars.get('project_base_name', 'default')
        self.initialize(**kwargs)
        set_timeout_async(lambda: iterm2.run_until_complete(self.coro))

    def initialize(self, **kwargs):
        pass

    @safe
    async def coro(self, connection):
        logging.info('TestTerm')
        app = await iterm2.async_get_app(connection)
        window = await get_window(app, self.project)
        if window is None:
            return
        session = window.current_tab.current_session
        await session.async_send_text('echo foo\r')
        await window.async_activate()


class StartTerm(_TermCommand):
    def initialize(self, ssh=None, **kwargs):
        self.ssh = ssh

    @safe
    async def coro(self, connection):
        logging.info('StartTerm')
        window = await create_window(connection, self.project)
        await window.current_tab.current_session.async_send_text(f"cd \"{self.vars['folder']}\"")
        


class CloseTerm(_TermCommand):
    @safe
    async def coro(self, connection):
        logging.info('CloseTerm: start')
        app = await iterm2.async_get_app(connection)
        logging.info('CloseTerm: have app')

        for session in app.buried_sessions:
            if project_name(session) == self.project:
                logging.info('CloseTerm: found session')
                await session.async_close()
                logging.info('CloseTerm: ssesion closed')
                return


class StartRepl(_TermCommand):
    def initialize(self, **kwargs):
        self.file_path = self.vars['file_path']
        self.file = self.vars['file']
        file, extension = self.vars['file_name'], self.vars['file_extension']
        self.cmd = {
            'jl': 'jl',
            'r': 'radian',
            'rmd': 'radian',
            'py': 'ipython'
        }.get(extension.lower(), None)
        # self.timeouts = 0

    @safe
    async def coro(self, connection):
        logging.info('StartRepl')
        app = await iterm2.async_get_app(connection)
        window = await get_window(app, self.project)
        if window is None:
            return

        window_project = await window.async_get_variable('user.project')
        if window_project != self.project:
            raise Exception("BAD PROJECT WINDOW")

        tmux = await get_tmux(connection, self.project)
        
        tab = await window.async_create_tmux_tab(tmux)
        TAB_IDS[self.file] = tab.tab_id
        await tab.async_set_title(self.vars['file_name'])
        await tab.current_session.async_set_variable('user.file', self.file)
        await tab.current_session.async_send_text(f"cd \'{self.file_path}\' && {self.cmd}\n")
        # code = b'\x1b' + b']1337;ClearScrollback' + b'\x07'
        # await tab.current_session.async_inject(code)

class TermSendText(_TermCommand):
    def initialize(self, text, **kwargs):
        self.text = text + '\n'

    @safe
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)
        window = await get_window(app, self.project)
        if window is None:
            return
        session = window.current_tab.current_session
        await session.async_send_text(self.text)
        await window.async_activate()


class LazyGit(_TermCommand):

    @safe
    async def coro(self, connection):
        app = await iterm2.async_get_app(connection)
        window = await get_window(app, self.project)
        if window is None:
            return

        # check if already exists and activate
        lg_tab = None
        for tab in window.tabs:
            for session in tab.sessions:
                if (await session.async_get_variable("user.lazygit")):
                    lg_tab = tab
                    break
        if lg_tab is None:
            cmd = f"zsh -dfic 'cd \"{self.vars['folder']}\" && /Users/fredcallaway/bin/lazygit'"
            tab = await window.async_create_tab(command=cmd)
            await tab.current_session.async_set_variable("user.lazygit", True)

        await tab.async_activate()
        await app.async_activate()


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

def project_name(session):
    return session.name.split(' ')[-1][:-1]

async def get_tmux(connection, project):
    # get tmux connection
    tmux_conns = await iterm2.async_get_tmux_connections(connection)
    for tmux_conn in tmux_conns:
        if project_name(tmux_conn.owning_session) == project:
            return tmux_conn
    
    raise Exception("Could not find tmux connection for " + project)


async def focus(connection, project, file_name=None):
    app = await iterm2.async_get_app(connection)
    window = await get_window(app, project)
    if window is None:
        return
    await window.async_activate()

    if file_name is not None:
        tab = await get_tab(app, file_name)
        if tab:
            await tab.async_activate()