#!/Users/fredcallaway/opt/miniconda3/bin/python

import iterm2
import sys
FOLDER = sys.argv[1]

async def main(connection):    
    app = await iterm2.async_get_app(connection)
    
    # # Foreground the app
    await app.async_activate()

    # folder = '/Users/fredcallaway/projects/recstrats'

    # check if already exists and activate
    for window in app.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                if await session.async_get_variable("user.lazygit-folder") == FOLDER:
                    print('Found session')
                    await session.async_activate()
                    return

    # Start in a new tab or window
    cmd = f"zsh -dfic 'cd \"{FOLDER}\" && /Users/fredcallaway/bin/lazygit'"
    myterm = app.current_terminal_window
    if not myterm:
        myterm = await iterm2.Window.async_create(connection, command=cmd)
    else:
        tab = await myterm.async_create_tab(command=cmd)

    session = myterm.tabs[0].sessions[0]
    await session.async_set_variable("user.lazygit-folder", FOLDER)
    await myterm.async_activate()

iterm2.run_until_complete(main)