import datetime
from fileinput import FileInput
from pathlib import Path
import os
import json
import typing as tp
from dataclasses import dataclass, field, asdict
import dataclasses
from functools import partial
from bisect import insort_right

# json utils ------------------------------------------------
class TaskJSONEncoder(json.JSONEncoder):
    def default(self, o): # pylint: disable=E0202
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

class TaskJSONDecoder(json.JSONDecoder):

    def __init__(self, *args, **kargs):
        super().__init__(object_hook=self.dict_to_object,
                             *args, **kargs)
    
    def dict_to_object(self, d): 
        return Task(**d)

JSON_PATH = Path('/home/mccloskey/Development/john/timelog/hourly_test.json')

# misc utils --------------------------------------

def timestamp_to_format(timestamp, format):
    return datetime.datetime.fromtimestamp(timestamp).strftime(format)

timestamp_to_HM = partial(timestamp_to_format, format='%H:%M')

get_cur_timestamp = datetime.datetime.now().timestamp

n_to_chr = lambda n: chr(n+97)
        

# structs ----------------------------------------------

@dataclass(order=True)
class Task:
    text: tp.List[str] = field(compare=False)
    inacitve: bool = True
    priority: int = 0 # negative is high priority, positive is low priority
    timestamp: datetime.datetime = field(default_factory=get_cur_timestamp)
    subtasks: tp.List['Task'] = field(default_factory=list, compare=False)
    finished: tp.Optional[datetime.datetime] = field(default=None, compare=False)


    @classmethod
    def from_text_str(cls, text, **kwargs):
        return cls(text.split('\n'), **kwargs)

    def __post_init__(self):
        self.subtasks.sort()

    def finish(self, note=None):
        self.finished = get_cur_timestamp()
        self.inacitve = True
        if note:
            self.text.append(note)

    def add_subtask(self, subtask):
        insort_right(self.subtasks, subtask)


    def __str__(self):
        inactive = ' ' if self.inacitve else '*'
        checkbox = f'[{timestamp_to_HM(self.finished)}]' if self.finished else '[ ]'
        text = '\n'.join(self.text)
        return f'{inactive}{checkbox} - {text}' + ''.join([f'\n  {subtask}' for subtask in self.subtasks])

class TaskList(list):

    @classmethod 
    def from_json(cls, path=JSON_PATH):
        with path.open() as f:
            return cls(json.load(f, cls=TaskJSONDecoder))

    def to_json(self, path=JSON_PATH):
        with path.open('w+') as f:
            json.dump(self, f, cls=TaskJSONEncoder)

    def print(self):
        print(*self, sep='\n')

    def insert_task(self, task_str_or_multistr, **kwargs):
        if isinstance(task_str_or_multistr, Task):
            task = task_str_or_multistr
        elif isinstance(task_str_or_multistr, str):
            task = Task.from_text_str(task_str_or_multistr, **kwargs)
        elif isinstance(task_str_or_multistr, list):
            task = Task(task_str_or_multistr, **kwargs)
        insort_right(self, task)



log_path = '/home/mccloskey/Desktop/hourly_out.txt'
TODOS_PATH = Path('/home/mccloskey/Desktop/todos.json')
accrued_logs = []
todos = TaskList.from_json()
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
        files = ['hourly_out.txt']
    else:
        files = [r'Notes',r'Daily\ Log','hourly_out.txt']
    for fname in files:
        os.system(f'xdg-open /home/mccloskey/Desktop/{fname}')

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

    return [l for l in get_last_day() if l.strip().startswith(('['))]

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
