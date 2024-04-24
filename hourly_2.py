from __future__ import annotations
from contextlib import contextmanager
import sys
import os
from pathlib import Path
import re

import typing as tp
import datetime
import readline

from todo_db import TodoDB
import todo_config

now = datetime.datetime.now


def open_files(paths: tp.Iterable[Path]) -> None:
    for p in paths:
        os.system(f"xdg-open {p.resolve()}")


def _get_rotated_filename(path: Path, i: int) -> Path:
    return path.with_name(f"{path.name}.{i}")


def rotate_file(path: Path, *, max_backups: int = 10) -> None:
    if not path.exists():
        return

    # Rename existing backup files
    for i in range(max_backups - 1, 0, -1):
        rotate_from = _get_rotated_filename(path, i)
        rotate_to = _get_rotated_filename(path, i + 1)
        if rotate_from.exists():
            rotate_from.rename(rotate_to)

    # Rename the original file to .1
    path.rename(_get_rotated_filename(path, 1))

    # Create a new empty file
    path.touch()


def alias(*aliases: str):
    def decorator(func):
        func.ALIASES = tuple(aliases)
        return func

    return decorator


class LogREPL:
    # CONFIGURATION ############################################################
    _BASE_DIR = Path.home() / "vault/logs"
    LOG_PATH = _BASE_DIR / "hourly_out.md"
    TODO_PATH = _BASE_DIR / "timelog_todo.db"
    HISTORY_PATH = _BASE_DIR / "timelog.history"

    # HELPERS ##################################################################

    @classmethod
    def _append_text(cls, text: str) -> None:
        with open(cls.LOG_PATH, mode="a") as f:
            f.write(f"{text}\n")

    @classmethod
    def _write_log(cls, text: str) -> None:
        msg = f"{now():%H:%M} - {text}"
        print(msg)
        cls._append_text(msg)

    @classmethod
    def _get_cmds(cls) -> tp.Iterable[tp.Callable[..., bool]]:
        attrs = (getattr(cls, name) for name in dir(cls) if name.startswith("CMD_"))
        return filter(callable, attrs)

    # COMMANDS #################################################################

    @classmethod
    @alias("T")
    def CMD_TODO(cls, *args: str, show_list_first: bool = True) -> bool:
        """Manage the todo list."""
        todo_path = cls.TODO_PATH
        if args and args[0].isdigit():
            todo_path = _get_rotated_filename(cls.TODO_PATH, int(args[0]))
        with TodoDB(todo_path) as todo_list:
            for a in args:
                todo_list.add_task(a)

            if show_list_first:
                print(todo_list)

            while True:
                inp = input(
                    "[P]rioritize, [F]inish, [A]dd, [S]how, [C]lear, [O]pen, [I]ssue? "
                )
                if not inp:
                    return True
                # see if command is one of the defaults -- letter + optional number
                cmd, id_, desc = re.match(r"(\D+)(\d*)(.*)", inp).groups()
                cmd = cmd.upper()
                id_ = int(id_) if id_ else None
                if cmd == "P":
                    task = todo_list.prioritize(id_)
                    cls._write_log(f"Priotized {task.description}")
                elif cmd == "F":
                    task = todo_list.mark_done(id_)
                    cls._write_log(f"Finished {task.description}")
                elif cmd == "A":
                    task = todo_list.add_task(desc, parent_id=id_)
                    cls._write_log(f"Added {task.description}")
                elif cmd == "S":
                    print(todo_list.show_task(id_))
                elif cmd in ["C", "CLEAR"]:
                    cls.CMD_CLEAR()
                elif cmd in ["O"]:
                    todo_config.open_task(id_ and todo_list[id_].issue_number)
                elif cmd == "I":
                    task = todo_list[id_]
                    if not desc.strip().isnumeric():
                        print(f"Invalid issue number: {desc}")
                        continue
                    task.issue_number = int(desc.strip())
                    cls._write_log(
                        f"Added issue number {task.issue_number} to {task.description}"
                    )

                else:
                    task = todo_list.add_task(inp)
                    cls._write_log(f"Added {task.description}")
                todo_list.commit()

    @classmethod
    def CMD_ROTATE_TODO(cls) -> bool:
        """Rotate the todo file."""
        rotate_file(cls.TODO_PATH)
        return True

    @classmethod
    def CMD_WHATADO(cls) -> bool:
        """Help! I don't know what to do!"""
        with TodoDB(cls.TODO_PATH) as todo_list:
            print(todo_list)
            print("Try breaking up the task into smaller tasks.")
            print(todo_list[0].format_tree())

        cls.CMD_TODO(show_list_first=False)
        return True

    @classmethod
    def CMD_QUIT(cls):
        """Quit the program."""
        return False

    @classmethod
    def CMD_NEWMEETING(cls, description: str) -> bool:
        """Start a new meeting."""
        text = f"""--- {now():%m/%d/%Y (%A)} {description} ---

 
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"""
        cls._append_text(text)
        return True

    @classmethod
    @alias("H")
    def CMD_HISTORY(cls) -> bool:
        print(cls.LOG_PATH.read_text())
        return True

    @classmethod
    @alias("O")
    def CMD_OPEN(cls):
        """Open the log file in the default text editor."""
        open_files([cls.LOG_PATH])
        return True

    @classmethod
    def CMD_NEWDAY(cls) -> bool:
        """Start a new day."""
        # show previous day
        cls.CMD_HISTORY()
        # start new day
        note = input("Note? ")
        cls._append_text(f"{now():---%m/%d/%Y (%A)---} {note}\nin {now():%H:%M}")

        # prompt for summary of yesterday and today
        for prompt in ["Yesterday, ", "Today, "]:
            cls._append_text(prompt + input(prompt))

        # prompt for meetings
        while description := input("Next meeting: "):
            cls.CMD_NEWMEETING(description)

        # finish checkin
        cls._write_log("finished checkin")
        cls.CMD_OPEN()
        return True

    @classmethod
    def _CMD_DEFAULT(cls, inp: str) -> bool:
        cls._write_log(inp)
        return True

    @classmethod
    def CMD_CLEAR(cls) -> bool:
        """Clear the screen."""
        _, lines = os.get_terminal_size()
        print("\n" * lines)
        return True

    @classmethod
    def CMD_HELP(cls) -> bool:
        print("Commands: ")
        for func in sorted(cls._get_cmds(), key=lambda f: f.__name__):
            names = [func.__name__.replace("CMD_", ""), *getattr(func, "ALIASES", [])]
            name = ", ".join(names)
            print(f"{name}: {func.__doc__ or ''}")
        return True

    # MAIN #####################################################################

    @classmethod
    def _get_cmd_and_args(cls, inp: str) -> tuple[tp.Callable[..., bool], list[str]]:
        if not inp:
            return cls.CMD_QUIT, []

        cmd, *args = inp.split(" ", maxsplit=1)
        cmd = cmd.upper()
        for func in cls._get_cmds():
            func_cmd = func.__name__[4:]
            if cmd in [func_cmd, *getattr(func, "ALIASES", [])]:
                break
        else:
            func = None

        NO_ARG_FUNCS = [cls.CMD_QUIT, cls.CMD_HISTORY, cls.CMD_OPEN]
        if func in NO_ARG_FUNCS and args:
            func = None

        if not func:
            return cls._CMD_DEFAULT, [inp]
        return func, args

    @classmethod
    @contextmanager
    def _state_context(cls):
        # setup
        print("Welcome to log! Config files:")
        for expected_path in [cls.LOG_PATH, cls.TODO_PATH, cls.HISTORY_PATH]:
            if not expected_path.exists():
                expected_path.touch()
            print(expected_path)

        readline.read_history_file(str(cls.HISTORY_PATH))
        readline.set_auto_history(True)
        readline.set_history_length(1000)
        try:
            yield
        except (KeyboardInterrupt, EOFError):
            print("Goodbye!")
        finally:
            readline.write_history_file(str(cls.HISTORY_PATH))

    @classmethod
    def main_loop(cls):
        with cls._state_context():
            # main loop
            cont = True
            while cont:
                inp = input("log: ")
                cmd, args = cls._get_cmd_and_args(inp)
                cont = cmd(*args)
                if cont is None:
                    raise ValueError(f"Command {cmd} returned None")

    @classmethod
    def main_once(cls, inp):
        cmd, args = cls._get_cmd_and_args(inp)
        cmd(*args)

    @classmethod
    def main(cls):
        if len(sys.argv) > 1:
            cls.main_once(" ".join(sys.argv[1:]))
        else:
            cls.main_loop()


if __name__ == "__main__":
    LogREPL.main()
