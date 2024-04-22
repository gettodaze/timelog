import datetime
from fileinput import FileInput
from pathlib import Path
import os
import json
import typing as tp
from dataclasses import dataclass, field, asdict
import dataclasses

# utils ------------------------------------------------
class TaskJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=E0202
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)

class TaskJSONDecoder(json.JSONDecoder):

    def __init__(self, *args, **kargs):
        super().__init__(object_hook=self.dict_to_object,
                             *args, **kargs)
    
    def dict_to_object(self, d): 
        d['timestamp'] = datetime.datetime.fromisoformat(d['timestamp'])
        d['finished'] = d['finished'] and datetime.datetime.fromisoformat(d['finished'])
        return Task(**d)

JSON_PATH = Path('/home/mccloskey/Development/john/timelog/hourly_test.json')

def load_todos():
    with JSON_PATH.open() as f:
        task_list = json.load(f, cls=TaskJSONDecoder)
    return task_list

def write_todos(task_list):
    with JSON_PATH.open('w+') as f:
        json.dump(task_list, f, cls=TaskJSONEncoder)

def datetime_to_HM(dt):
    return dt.strftime('%H:%M')
        

# structs ----------------------------------------------

@dataclass(order=True)
class Task:
    text: tp.List[str] = field(compare=False)
    priority: int = 0
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now().isoformat)
    subtasks: tp.List['Task'] = field(default_factory=list, compare=False)
    finished: tp.Optional[datetime.datetime] = field(default=None, compare=False)

    @classmethod
    def from_text_str(cls, text):
        return cls(text.split('\n'))

    @classmethod
    def to_json_dict(cls, task):
        update = {
            'subtasks': [Task.to_json_dict(subtask) for subtask in task.subtasks],
            'timestamp': str(task.timestamp),
            'finished': str(task.finished) if task.finished else task.finished
        }
        return {**asdict(task), **update}

    def finish(self, note=None):
        self.finished = datetime.datetime.now()
        if note:
            self.text.append(note)

    def add_subtask(self, subtask):
        self.subtasks.append(subtask)

    def __str__(self, prefix=''):
        checkbox = f'[{datetime_to_HM(self.finished)}]' if self.finished else '[ ]'
        text = '\n'.join(self.text)
        return f'{prefix} {checkbox} - {text}' + ''.join([f'\n  {prefix}{strsubtask}' for subtask in sorted(self.subtasks)])


log_path = '/home/mccloskey/vault/logs/hourly_out.md'
TODOS_PATH = Path('/home/mccloskey/Desktop/todos.json')
accrued_logs = []
# todos = [Task.from_json_dict(d) for d in json.loads(TODOS_PATH.read_text())]
# breakpoint()

def replace_line(old, new):
    with FileInput(files=[log_path], inplace=True) as f:
        for line in f:
            print(line if line != old else new, end='')

def leading_0(n):
    if 0 <= n < 10:
        return f'0{n}'
    else:
        return str(n)

def write_log(log):
    with open(log_path, mode='a+') as f:
        f.write(f'{log}\n')

def get_last_day():
    with open(log_path, mode='r') as f:
        lines = f.readlines()
    for i in range(len(lines)-1,0,-1):
        if lines[i].startswith('-----'):
            break
    return lines[i-1:]

def print_last_day():
    print(''.join(get_last_day()))



def open_logs(only_hourly_out=False):
    if only_hourly_out:
        files = ['hourly_out.md']
    else:
        files = ['notes.md','daily_log.md','hourly_out.md']
    for fname in files:
        os.system(f'xdg-open /home/mccloskey/vault/logs/{fname}')

def format_meeting(description):
        return f'''--- {datetime.datetime.now().strftime("%m/%d/%Y (%A)")} {description} ---

 
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'''

def get_meetings():
    meetings = []
    cont = True
    while cont:
        desc = input('Next meeting: ')
        if desc.upper() in ['N', 'NO', 'NONE', '']:
            return meetings
        meetings.append(desc)

def get_todos():

    return [l for l in get_last_day() if l.startswith(('['))]

def write_todo(todo):
    now = datetime.datetime.now()
    log = f'[ ] {todo} # {now.strftime("%H:%M")}'
    write_log(log)
    return log

def write_todos(todo_str, echo=False):    
    for todo in todo_str.split(';'):
        log = write_todo(todo)
        print(log)

def finish_todo(enum, note):
    finished_str = get_todos()[int(enum)]
    replace = finished_str.replace('[ ]', f'[{datetime.datetime.now().strftime("%H:%M")}]')
    replace_line(finished_str, f'{replace.strip()}{note}\n')

def todo_loop():
    while True:
        for i, todo in enumerate(get_todos()):
            print(i, todo, end='')
        while True:
            finished = input('finished a todo? ')
            if finished.upper() in ['', 'N']:
                return
            finished_args = finished.split(' ', maxsplit=1)
            enum = finished_args[0]
            if enum.isdigit():
                break
            if len(finished_args) == 2 and enum.upper() in ['ADD', 'NEW']:
                write_todos(finished_args[1])
                continue
            else:
                print('invalid enum', enum)
        note = '' if len(finished_args) < 2 else ' - '+finished_args[1]
        finish_todo(enum, note)

def newday(note):
    if datetime.datetime.now().weekday() == 4: #friday
        input('Dont forget to book the pool for tomorrow!')
    log = datetime.datetime.now().strftime('---%m/%d/%Y (%A)---')+f' {note}\n'+datetime.datetime.now().strftime('in %H:%M')
    print_last_day()
    write_log(log)
    write_log('Yesterday, '+input('Yesterday, '))
    todos_str = input('Today, ')
    write_log('Today, ' + todos_str)
    meetings = get_meetings()
    for m in meetings:
        write_log(f'> {m}')
    for m in meetings:
        write_log(format_meeting(m))
    write_log('\nTODO:')
    write_todos(todos_str)
    write_log('\n')
    write_log(f'{datetime.datetime.now().strftime("%H:%M")} - finished checkin')
    open_logs()


def parse_and_handle_input():
    inp = input('log: ')
    args = inp.split(' ', maxsplit=1)
    nargs = len(args)
    if nargs == 0:
        return True
    if nargs == 1:
        if args[0].upper() in ['Q', 'QUIT']:
            return False
        if args[0].upper() in ['H','HISTORY']:
            print_last_day()
            return True
        if args[0].upper() in ['FP','FILEPATH']:
            print(log_path)
            return True
        if args[0].upper() in ['O','OPEN']:
            open_logs(only_hourly_out=True)
            return True
        if args[0].upper() in ['OALL']:
            open_logs(only_hourly_out=False)
            return True
        if args[0].upper() in ['T','TIME']:
            print(datetime.datetime.now())
            return True
        if args[0].upper() == 'RAPC':
            os.system('code ~/Development/rapc')
            return True
        if args[0].upper() in ['TODO', 'TODOS']:
            todo_loop()
            return True
        
    now = datetime.datetime.now()
    if args[0].upper() in ['NEWDAY']:
        note = input('note? ') if nargs == 1 else args[1]
        newday(note)
        return True
    elif args[0].upper() in ['TODO']:
        write_todos(args[1], echo=True)
        return True
    elif args[0].upper() in ['NEWMEETING']:
        write_log(format_meeting(args[1]))
        return True
    else:
        log = f'{now.hour}:{leading_0(now.minute)} - {inp}'
        write_log(log)
        print(log)
        return True


def main():
    cont = True
    while cont:
        cont = parse_and_handle_input()

if __name__ == "__main__":
    main()
