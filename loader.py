# https://stackoverflow.com/a/66558182/16126645

from itertools import cycle
from shutil import get_terminal_size
from threading import Thread
from time import sleep

from config import params


class Loader:
    def __init__(self, desc="Loading...", end="", timeout=0.1, step_type=0, detailed=None):
        """
        A loader-like context manager

        Args:
            desc (str, optional): The loader's description. Defaults to "Loading...".
            end (str, optional): Final print. Defaults to "Done!".
            timeout (float, optional): Sleep time between prints. Defaults to 0.1.
        """
        self.desc = desc
        self.end = end
        self.timeout = timeout
        self.detailed = detailed

        if params['threaded']:
            self._thread = Thread(target=self._animate, daemon=True)
        self.step_options = [
            ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"],
            ["⢻", "⣹", "⣼", "⣶", "⣧", "⣏", "⡟", "⠿"],
            ["|", "/", "-", "\\"],
        ]
        self.steps = self.step_options[step_type]
        self.done = False

    def start(self):
        if self.detailed and not params['detailed']:
            return self
        if self.detailed == False and params['detailed']:
            return self
        if not params['threaded']:
            print(f"{self.desc}", end="", flush=True)
            return self
        self._thread.start()
        return self

    def _animate(self):
        for c in cycle(self.steps):
            if self.done:
                break
            print(f"\r{c} {self.desc}", flush=True, end="")
            sleep(self.timeout)

    def __enter__(self):
        self.start()

    def stop(self):
        self.done = True
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


if __name__ == "__main__":
    with Loader("Loading with context manager..."):
        for i in range(10):
            sleep(0.25)

    loader = Loader("Loading with object...", "That was fast!", 0.05).start()
    for i in range(10):
        sleep(0.25)
    loader.stop()