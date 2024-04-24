from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from contextlib import contextmanager, AbstractContextManager

from sqlalchemy import Boolean, create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

# Create an engine

# Create a base class for our declarative class definitions
Base = declarative_base()


# Define the Task class
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("tasks.id"))
    done = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    issue_number = Column(Integer, nullable=True)

    subtasks = relationship("Task", order_by="asc(Task.done), asc(Task.priority)")

    def __repr__(self):
        return f"Task({self.id}, {self.description!r}, parent_id={self.parent_id!r})"

    def format_tree(*tasks: Task) -> str:
        print(tasks)
        seen = set()

        def _format_tree(task: Task, indent: int) -> str:
            seen.add(task.id)
            prefix = f"{' ' * indent}[{'x' if task.done else ' '}]"
            main_task = f"{prefix} {task.id} {task.description}\n"
            subtasks = "".join(
                _format_tree(subtask, indent + 2) for subtask in task.subtasks
            )
            return main_task + subtasks

        return "\n".join(_format_tree(task, 0) for task in tasks if task.id not in seen)

    def prioritize(self) -> None:
        self.priority -= 1


@lru_cache(4)
def _get_sessionmaker(fp: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{fp.resolve()}", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


# Create the tables


@contextmanager
def _session_scope(fp: Path):
    """Provide a transactional scope around a series of operations."""
    session = _get_sessionmaker(fp)()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class TodoDB(AbstractContextManager):
    def __init__(self, fp: Path):
        self.fp = fp
        self._session = None

    def __enter__(self):
        self._session = _get_sessionmaker(self.fp)()
        return self

    @property
    def session(self):
        if self._session is None:
            raise ValueError(
                "Session not open. Are you using this outside of a `with` block?"
            )
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()

    @property
    def tasks(self):
        return self.session.query(Task).order_by(Task.done, Task.priority.desc()).all()

    def add_task(self, description: str, parent_id=None) -> Task:
        task = Task(description=description, parent_id=parent_id)
        self.session.add(task)
        return task

    def mark_done(self, task_id: int) -> Task:
        task = self.session.query(Task).get(task_id)
        task.done = True
        return task

    def prioritize(self, task_id: int) -> Task:
        task = self.session.query(Task).get(task_id)
        task.prioritize()
        return task

    def show_task(self, idx) -> str:
        return self[idx].format_tree() if idx else str(self)

    def delete_task(self, idx):
        task = self.session.query(Task).get(idx)
        self.session.delete(task)

    def __getitem__(self, idx):
        return self.session.query(Task).get(idx)

    def __str__(self):
        return Task.format_tree(*self.tasks)

    def commit(self):
        self.session.commit()
