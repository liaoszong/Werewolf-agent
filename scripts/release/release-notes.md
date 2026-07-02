# Werewolf-agent 0.2.0

- For first install, download `Werewolf-agent-0.2.0-Setup.exe` only.
- Other assets (`.nupkg`, release indexes, and packaging outputs) are for the Velopack updater and should not be selected manually.
- First Windows desktop distribution build.
- Installs the PyInstaller bootstrapper, Qt client, and frozen observer server as one desktop app.
- Adds client-owned update UI for version, release notes, download status, failure state, and restart.
- Keeps runs, profiles, configs, local credentials, and settings outside the replaceable app directory.

Known limitation: this installer is not code-signed yet, so Windows may show an "Unknown publisher" or SmartScreen warning before installation.
