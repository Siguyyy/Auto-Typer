# Auto Typer

Auto Typer is a small Windows desktop practice tool for typing an essay from memory. It shows the current word in an always-on-top prompt while a global keyboard listener tracks progress in another editor such as Google Docs.

## Requirements

- Windows
- Python 3.10 or newer
- A trusted Python environment

## Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\essay_typing_prompt.py
```

You can also double-click `Run Essay Typing Prompt.bat` after installing the dependency.

## Use it

1. Paste or type an essay into the first window.
2. Select **Start practice**.
3. Switch to your editor and type normally. The prompt advances when the expected characters are entered.
4. Close the prompt when finished; this stops the keyboard listener.

The app reports accepted characters, remaining characters, active typing time, and an approximate words-per-minute rate. It does not save or transmit the essay or keystrokes.

## Windows executable

The source distribution intentionally does not include generated PyInstaller build output. Build your own executable with a trusted local PyInstaller installation if needed:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name "Auto Typer" essay_typing_prompt.py
```

## Privacy and permissions

Practice mode observes keyboard input system-wide so it can work while another application has focus. Review Windows security prompts carefully, do not use it while entering passwords or other sensitive data, and close the practice window to stop observation. See [SECURITY.md](SECURITY.md) for the security boundary.

