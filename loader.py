# https://stackoverflow.com/a/66558182/16126645

from itertools import cycle
from shutil import get_terminal_size
from threading import Thread
from time import sleep

from config import params

class Loader:
    def __init__(
            self, desc: str = "Loading...", end: str = "", timeout: float = 0.1, step_type: int = 0, 
            check_type: int = 2, detailed: bool | None = None, count: int = 0, enabled: bool = True
        ) -> None:
        """A loader-like context manager

        Args:
            desc (str, optional): The loader's description. Defaults to "Loading..."
            end (str, optional): Final print. Defaults to "".
            timeout (float, optional): Sleep time between prints. Defaults to 0.1.
            step_type (int, optional): The step icon to display. Defaults to option 0.
            check_type (int, optional): The check icon to display. Defaults to option 2.
            detailed (bool | None, optional): Whether to show detailed output. Defaults to None.
            count (int, optional): The count to display. Defaults to 0.
            enabled (bool, optional): Defaults to True.
        """
        self.desc = desc
        self.end = end
        self.timeout = timeout
        self.detailed = detailed
        self.count = True if count else False
        self.count_int = count
        self.enabled = enabled

        if params['threaded']:
            self._thread = Thread(target=self._animate, daemon=True)
        self.step_options = [
            ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"],
            ["⢻", "⣹", "⣼", "⣶", "⣧", "⣏", "⡟", "⠿"],
            ["|", "/", "-", "\\"],
        ]
        self.completed_options = [
            "⣿", "⠀", "✓"
        ]
        self.steps = self.step_options[step_type]
        self.check = self.completed_options[check_type]
        self.done = False

    def start(self):
        if params["headless"] or not self.enabled: 
            return self
        if self.detailed and not params['detailed']:
            return self
        if self.detailed == False and params['detailed']:
            return self
        if not params['threaded']:
            print(f"{self.desc}{f' {self.count_int}' if self.count else ''}", end="", flush=True)
            return self
        self._thread.start()
        return self

    def _animate(self):
        if params["headless"] or not self.enabled:
            return
        for c in cycle(self.steps):
            if self.done:
                break
            print(f"\r{c} {self.desc}{f' {self.count_int}...' if self.count else ''}", flush=True, end="")
            if self.count_int:
                self.count_int -= 1
            sleep(self.timeout)

    def __enter__(self):
        self.start()

    def stop(self):
        if params["headless"] or not self.enabled:
            return
        self.done = True
        print(f"\r{self.check} {self.desc}{f' {self.count_int}' if self.count else ''}", flush=True, end="")
        if self.detailed and not params['detailed']:
            return
        if self.detailed == False and params['detailed']:
            return
        cols = get_terminal_size((80, 20)).columns
        line_start = "\n"
        if params['flush_prints']:
            print("\r" + " " * cols, end="", flush=True)
            line_start = "\r"
        print(f"{line_start}{self.end}", flush=True, end="\n" if self.end else f"\r")

    def __exit__(self, exc_type, exc_value, tb):
        # handle exceptions with those variables ^
        self.stop()
    
    def update_description(self, desc: str):
        self.desc = desc
        cols = get_terminal_size((80, 20)).columns
        print("\r" + " " * cols, end="", flush=True)