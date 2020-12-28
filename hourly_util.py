import json
import datetime
from pathlib import Path

'''
multistr = list of strings where each string is a newline
timestamp = string datetime.datetime.now()
todo: {
    timestamp, 
    text: multistr,
    finished: timestamp,
    subtasks: list[todo...]
}
note: {
    timestamp,
    title: multistr,
    text: multistr
}
day: {
    journal: multistr
    check-in: multistr
    notes: [note...]
    log: {time_timestamp, text: multistr}
}
file: {
    todos: [todo...]
    day_timestamp: day...
}
'''

JSON_PATH = Path('/home/mccloskey/Development/john/timelog/hourly_test.txt')
TXT_PATH = Path('/home/mccloskey/Development/john/timelog/hourly_test.json')
TXT2_PATH = Path('/home/mccloskey/Development/john/timelog/hourly_test2.json')

def load_json():
    with JSON_PATH.open() as f:
        ret = json.load(f)
    return ret

def write_json(d):
    with JSON_PATH.open('w+') as f:
        json.dump(d, f)

def load_text(text=None):
    text = text or TXT_PATH.read_text()

def write_text(d):
    with TXT2_PATH.open('w+') as f:
        pass

def write_todos(todos, indent=0):
    out_multistr = []
    for todo in todos:
        out_multistr.append(f'')

# -----------------------------------------
def load_hourmin(day=None):
    day = day or datetime.date.today()



    
    






