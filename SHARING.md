# Sharing this program

## Easiest: make one Windows `.exe`

On the computer that has this project, open PowerShell in this folder and run:

```powershell
py -m pip install pyinstaller
py -m PyInstaller --noconsole --onefile --name "Essay Typing Prompt" --collect-submodules pynput essay_typing_prompt.py
```

Share the resulting `dist\Essay Typing Prompt.exe`. The recipient does **not** need Python or any packages. Windows may show a SmartScreen warning for a newly-created unsigned program; only share it with people who trust you.

## Share the source instead

Send the whole folder containing `essay_typing_prompt.py`, `Run Essay Typing Prompt.bat`, and `requirements.txt`.

The recipient needs Windows with Python 3 installed. They run this once in that folder:

```powershell
py -m pip install -r requirements.txt
```

Then they can double-click `Run Essay Typing Prompt.bat`.
