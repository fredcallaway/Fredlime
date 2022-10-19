from sublime_plugin import WindowCommand, TextCommand
from sublime import Region

import platform
import iterm2

class LazyGit(WindowCommand):
    def run(self, **kwargs):
        self.folder = self.window.extract_variables()['folder']
        # subprocess.check_call([here('lazygit.py'), self.folder])
        self.test()

    def test(self):
        try:
            iterm2.run_until_complete(self.lazygit)
        except:
            print('lazygit error')

    async def lazygit(self, connection):   
        app = await iterm2.async_get_app(connection)
        
        # Foreground the app
        await app.async_activate()

        # check if already exists and activate
        for window in app.windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    folder = await session.async_get_variable("user.lazygit-folder")
                    print('folder', folder)
                    if folder == self.folder:
                        print('Found session')
                        await session.async_activate()
                        return

        # self.folder = '/Users/fredcallaway/projects/recstrats'

        # Start in a new tab or window
        cmd = f"zsh -dfic 'cd \"{self.folder}\" && /Users/fredcallaway/bin/lazygit'"
        myterm = app.current_terminal_window
        if not myterm:
            myterm = await iterm2.Window.async_create(connection, command=cmd)
        else:
            tab = await myterm.async_create_tab(command=cmd)

        session = myterm.current_tab.current_session
        await session.async_set_variable("user.lazygit-folder", self.folder)
        await myterm.async_activate()


async def test(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_terminal_window.tabs[0].sessions[0]
    await session.async_send_text('x = 1\n')

