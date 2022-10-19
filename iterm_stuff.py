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
            iterm2.run_until_complete(lazygit)
        except:
            print('lazygit error')


async def test(connection):
    app = await iterm2.async_get_app(connection)
    session = app.current_terminal_window.tabs[0].sessions[0]
    await session.async_send_text('x = 1\n')


async def lazygit(connection):   
    app = await iterm2.async_get_app(connection)
    folder = '/Users/fredcallaway/projects/recstrats'
    
    # Foreground the app
    await app.async_activate()

    # self.folder = '/Users/fredcallaway/projects/recstrats'

    # Start in a new tab or window
    cmd = f"zsh -dfic 'cd \"{folder}\" && /Users/fredcallaway/bin/lazygit'"
    myterm = app.current_terminal_window
    if not myterm:
        myterm = await iterm2.Window.async_create(connection, command=cmd)
    else:
        tab = await myterm.async_create_tab(command=cmd)

    session = myterm.tabs[0].sessions[0]
    print('about to set variable')
    await session.async_set_variable("user.testvar", 'test')
    print('success!')
    await myterm.async_activate()
