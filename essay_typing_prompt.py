"""A distraction-free, always-on-top essay typing prompt for Windows.

Paste an essay, click Start practice, then type the word shown in the black
window. A global keyboard listener advances the prompt even while you
are typing in another app such as Google Docs.
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox
from pynput import keyboard


WINDOW_SIZE = 520
ACTIVE_TYPING_GAP_SECONDS = 2.5
STATS_REFRESH_MS = 250


class EssayTypingPrompt:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Essay typing prompt")
        # Grid reserves a dedicated bottom row for the button. This keeps it
        # visible on high-DPI displays instead of letting the text box crowd it
        # out of the window.
        self.root.minsize(560, 500)
        self.root.geometry("720x650")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        self.words: list[str] = []
        self.word_index = 0
        self.character_index = 0
        self.prompt_window: tk.Toplevel | None = None
        self.character_label: tk.Label | None = None
        self.progress_label: tk.Label | None = None
        self.wpm_label: tk.Label | None = None
        self.remaining_label: tk.Label | None = None
        self.active_time_label: tk.Label | None = None
        self.keyboard_listener: keyboard.Listener | None = None
        self.accepted_characters = 0
        self.target_characters = 0
        self.active_seconds = 0.0
        self.last_key_time: float | None = None
        self.practice_complete = False

        tk.Label(
            root,
            text="Paste your essay below, then click Start practice.",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))

        tk.Label(
            root,
            text="Then click back into Google Docs (or any editor) and type normally.",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        self.input_box = tk.Text(root, wrap="word", font=("Segoe UI", 11), undo=True)
        self.input_box.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 14))
        self.input_box.focus_set()

        button_row = tk.Frame(root)
        button_row.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        tk.Button(
            button_row,
            text="Start practice",
            command=self.start,
            font=("Segoe UI", 11, "bold"),
            padx=16,
            pady=7,
        ).pack()

    def start(self) -> None:
        # Tk Text appends a newline at the end; remove only that automatic one.
        essay = self.input_box.get("1.0", "end-1c")
        if not essay:
            messagebox.showwarning("No essay", "Paste or type an essay first.")
            return

        # split() removes only the gaps between words. Thus punctuation that is
        # attached to a word (such as "world.") remains part of that prompt.
        self.words = essay.split()
        if not self.words:
            messagebox.showwarning("No essay", "Paste or type an essay first.")
            return

        self.word_index = 0
        self.character_index = 0
        self.accepted_characters = 0
        self.target_characters = len(essay)
        self.active_seconds = 0.0
        self.last_key_time = None
        self.practice_complete = False
        self.root.withdraw()  # The input window disappears while practising.
        self.open_prompt()

    def open_prompt(self) -> None:
        prompt = tk.Toplevel(self.root)
        self.prompt_window = prompt
        prompt.title("Essay typing prompt")
        prompt.configure(bg="black")
        prompt.attributes("-topmost", True)
        prompt.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        prompt.minsize(320, 320)
        prompt.protocol("WM_DELETE_WINDOW", self.close_prompt)

        # Keeping normal window decorations leaves the usual X close button.
        self.character_label = tk.Label(
            prompt,
            bg="black",
            fg="white",
            font=("Segoe UI", 56, "bold"),
            wraplength=460,
            justify="center",
        )
        self.character_label.pack(expand=True, fill="both", padx=20, pady=(35, 0))

        stats_frame = tk.Frame(prompt, bg="black")
        stats_frame.pack(fill="x", padx=18, pady=(0, 8))
        self.wpm_label = tk.Label(
            stats_frame,
            bg="black",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self.wpm_label.pack(fill="x")
        self.remaining_label = tk.Label(
            stats_frame,
            bg="black",
            fg="#d0d0d0",
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.remaining_label.pack(fill="x", pady=(3, 0))
        self.active_time_label = tk.Label(
            stats_frame,
            bg="black",
            fg="#d0d0d0",
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.active_time_label.pack(fill="x", pady=(3, 0))

        self.progress_label = tk.Label(
            prompt,
            bg="black",
            fg="#bdbdbd",
            font=("Segoe UI", 10),
        )
        self.progress_label.pack(pady=(0, 18))

        self.start_keyboard_listener()
        self.update_display()
        self.refresh_stats()

    def start_keyboard_listener(self) -> None:
        """Listen system-wide without taking focus away from the user's editor."""
        self.keyboard_listener = keyboard.Listener(on_press=self.global_key_pressed)
        self.keyboard_listener.start()

    def global_key_pressed(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Receive a keystroke from any foreground application.

        pynput invokes this method on a non-Tk thread, so the visible update is
        scheduled safely on Tk's own event loop.
        """
        if key == keyboard.Key.space:
            typed = " "
        elif key == keyboard.Key.enter:
            typed = "\n"
        elif key == keyboard.Key.tab:
            typed = "\t"
        else:
            typed = getattr(key, "char", None)

        try:
            self.root.after(0, self.process_key, typed)
        except tk.TclError:
            # The listener can receive a final key while the window is closing.
            pass

    def process_key(self, typed: str | None) -> None:
        """Record typing activity, then process a printable key if there is one."""
        if not self.prompt_window or self.practice_complete:
            return

        self.record_activity()
        if typed:
            self.process_character(typed)
        self.render_stats()

    def record_activity(self) -> None:
        """Accumulate only intervals that are part of an active typing burst."""
        now = time.monotonic()
        if self.last_key_time is not None:
            self.active_seconds += min(now - self.last_key_time, ACTIVE_TYPING_GAP_SECONDS)
        self.last_key_time = now

    def process_character(self, typed: str) -> None:
        """Match typed characters against the current displayed word."""
        if not self.prompt_window or self.word_index >= len(self.words):
            return

        # Spaces, tabs, and line breaks are separators in the document; the
        # displayed words deliberately never include them.
        if typed.isspace():
            self.accepted_characters += 1
            return

        current_word = self.words[self.word_index]
        expected = current_word[self.character_index]

        if typed == expected:
            self.accepted_characters += 1
            self.character_index += 1
            if self.character_index == len(current_word):
                self.word_index += 1
                self.character_index = 0
            if self.word_index == len(self.words):
                self.finish()
            else:
                self.update_display()
        else:
            self.flash_incorrect()

    def update_display(self) -> None:
        if not self.character_label or not self.progress_label:
            return
        self.character_label.configure(text=self.words[self.word_index], fg="white")
        self.progress_label.configure(
            text=f"Word {self.word_index + 1} of {len(self.words)}  •  Type the whole word, including punctuation"
        )

    def current_active_seconds(self) -> float:
        """Include the current short typing burst without counting long pauses."""
        if self.practice_complete or self.last_key_time is None:
            return self.active_seconds
        return self.active_seconds + min(time.monotonic() - self.last_key_time, ACTIVE_TYPING_GAP_SECONDS)

    @staticmethod
    def format_duration(seconds: float) -> str:
        total_seconds = max(0, round(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02}:{seconds:02}"
        return f"{minutes}:{seconds:02}"

    def render_stats(self) -> None:
        if not self.wpm_label or not self.remaining_label or not self.active_time_label:
            return

        active_time = self.current_active_seconds()
        wpm = 0.0 if active_time < 1 else (self.accepted_characters / 5) / (active_time / 60)
        remaining_characters = max(0, self.target_characters - self.accepted_characters)
        if wpm > 0:
            remaining = self.format_duration((remaining_characters / 5) / wpm * 60)
        else:
            remaining = "--:--"

        self.wpm_label.configure(text=f"Average speed: {wpm:.1f} WPM")
        self.remaining_label.configure(text=f"Estimated remaining: {remaining}")
        self.active_time_label.configure(text=f"Active typing time: {self.format_duration(active_time)}")

    def refresh_stats(self) -> None:
        """Keep the counters live while a typing session is in progress."""
        if not self.prompt_window:
            return
        self.render_stats()
        if not self.practice_complete:
            self.prompt_window.after(STATS_REFRESH_MS, self.refresh_stats)

    def flash_incorrect(self) -> None:
        if not self.character_label or not self.prompt_window:
            return
        self.character_label.configure(fg="#ff5757")
        self.prompt_window.after(150, lambda: self.character_label and self.character_label.configure(fg="white"))

    def finish(self) -> None:
        if not self.character_label or not self.progress_label:
            return
        self.practice_complete = True
        self.render_stats()
        self.character_label.configure(text="DONE", fg="#7CFF7C", font=("Segoe UI", 50, "bold"))
        self.progress_label.configure(text="You completed the essay. Close this window with X.")

    def close_prompt(self) -> None:
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        if self.prompt_window:
            self.prompt_window.destroy()
            self.prompt_window = None
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    EssayTypingPrompt(app_root)
    app_root.mainloop()
