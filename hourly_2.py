from __future__ import annotations
from contextlib import contextmanager
import os
from pathlib import Path

import typing as tp
import datetime
import readline

from todo_db import TodoDB

now = datetime.datetime.now

def open_files(paths: tp.Iterable[Path]) -> None:
    for p in paths:
        os.system(f'xdg-open {p.resolve()}')

def _get_rotated_filename(path: Path, i: int) -> Path:
    return path.with_name(f"{path.name}.{i}")

def rotate_file(path: Path, *, max_backups: int = 10) -> None:
    if not path.exists():
        return

    # Rename existing backup files
    filename = path.name
    for i in range(max_backups - 1, 0, -1):
        rotate_from = _get_rotated_filename(path, i)
        rotate_to = _get_rotated_filename(path, i + 1)
        if rotate_from.exists():
            rotate_from.rename(rotate_to)

    # Rename the original file to .1
    path.rename(_get_rotated_filename(path, 1))

    # Create a new empty file
    path.touch()

class LogREPL:
    # CONFIGURATION ############################################################

    LOG_PATH = Path('/tmp/timelog.txt')
    TODO_PATH = Path('/tmp/timelog_todo.db')
    CMD_HISTORY_PATH = Path('/tmp/timelog.history')

    # HELPERS ##################################################################
    
    @classmethod
    def _append_text(cls, text: str) -> None:
        with open(cls.LOG_PATH, mode='a') as f:
            f.write(f'{text}\n')

    @classmethod
    def _write_log(cls, text: str) -> None:
        cls._append_text(f"{now():%H:%M} - {text}")

    # COMMANDS #################################################################

    @classmethod
    def CMD_TODO(cls, *args: str, show_list_first: bool = True) -> bool:
        todo_path = cls.TODO_PATH
        if args and args[0].isdigit():
            todo_path = _get_rotated_filename(cls.TODO_PATH, int(args[0]))
        with TodoDB(todo_path) as todo_list:
            for a in args:
                todo_list.add_task(a)
            
            if show_list_first:
                print(todo_list)
            
            while True:
                split = input('QPDA? ').split(' ', maxsplit=1)
                cmd = split[0].upper()
                if cmd == 'Q':
                    return True
                elif cmd[0] == 'P':
                    task = todo_list.prioritize(int(cmd[1:]))
                    cls._write_log(f"Priotized {task.description}")
                elif cmd[0] == 'D':
                    task = todo_list.mark_done(int(cmd[1:]))
                    cls._write_log(f"Finished {task.description}")
                elif cmd[0] == 'A':
                    parent_id=int(cmd[1:]) if len(cmd) > 1 else None
                    task = todo_list.add_task(split[1], parent_id=parent_id)
                    cls._write_log(f"Added {task.description}")
                elif cmd == 'CLEAR':
                    cls.CMD_CLEAR()
                else:
                    print('Invalid command. Use Q, P, D, or A')
                todo_list.commit()
                print(todo_list)

    @classmethod
    def CMD_ROTATE_TODO(cls) -> bool:
        rotate_file(cls.TODO_PATH)
        return True

    @classmethod
    def CMD_WHATADO(cls) -> bool:
        with TodoDB(cls.TODO_PATH) as todo_list:
            print(todo_list)
            print('Try breaking up the task into smaller tasks.')
            print(todo_list[0].format_tree())

        cls.CMD_TODO(show_list_first=False)
        return True


    @classmethod
    def CMD_QUIT(cls):
        return False
    
    @classmethod
    def CMD_NEWMEETING(cls, description: str) -> bool:
        text = f'''--- {now():%m/%d/%Y (%A)} {description} ---

 
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'''
        cls._append_text(text)
        return True
    
    @classmethod
    def CMD_HISTORY(cls) -> bool:
        print(cls.LOG_PATH.read_text())
        return True

    @classmethod
    def CMD_OPEN(cls):
        open_files([cls.LOG_PATH])
        return True
    
    @classmethod    
    def CMD_NEWDAY(cls) -> bool:
        # show previous day
        cls.CMD_HISTORY()
        # start new day
        note = input("Note? ")
        cls._append_text(f"{now():---%m/%d/%Y (%A)---} {note}\nin {now():%H:%M}")

        # prompt for summary of yesterday and today
        for prompt in ['Yesterday, ', 'Today, ']:
            cls._append_text(prompt+input(prompt))
        
        # prompt for meetings
        while description := input('Next meeting: '):
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
        _, lines = os.get_terminal_size()
        print('\n'*lines)
        return True
    
    
    # Aliases
    CMD_Q = CMD_QUIT
    CMD_H = CMD_HISTORY
    CMD_O = CMD_OPEN







    # MAIN #####################################################################
    
    @classmethod
    def _get_cmd_and_args(cls, inp: str) -> tuple[tp.Callable[..., bool], list[str]]:
        cmd, *args = inp.split(' ', maxsplit=1)
        func = getattr(cls, f'CMD_{cmd.upper()}', None)

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
        print('Welcome to log! Config files:')
        for expected_path in [cls.LOG_PATH, cls.TODO_PATH, cls.CMD_HISTORY_PATH]:
            if not expected_path.exists():
                expected_path.touch()
            print(expected_path)

        
        
        readline.read_history_file(str(cls.CMD_HISTORY_PATH))
        readline.set_auto_history(True)
        readline.set_history_length(1000)
        try:
            yield
        except (KeyboardInterrupt, EOFError):
            print("Goodbye!")
        finally:
            readline.write_history_file(str(cls.CMD_HISTORY_PATH))

        
    @classmethod
    def main(cls):
        with cls._state_context():
            # main loop
            cont = True
            while cont:
                inp = input('log: ')
                cmd, args = cls._get_cmd_and_args(inp)
                cont = cmd(*args)
                if cont is None:
                    raise ValueError(f'Command {cmd} returned None')

if __name__ == '__main__':
    LogREPL.main()