"""Daily tasks: DailyTask (one goal) and DailyTaskManager (today's set).

Tasks are data-driven. A TaskSpec from settings.DAILY_TASK_POOL says which
profile event a task listens to ("game_played", "tickets_earned", ...), the
target and the reward; DailyTask applies that to its own progress. Adding a
task means adding a pool entry, not a class.

The manager picks DAILY_TASK_COUNT specs when the calendar date changes,
feeds events to the tasks, and hands out each reward once. Like
DailyRewardManager it never touches tokens: PlayerProfile.claim_task() pays.
"""
import random
from dataclasses import dataclass

from game_clock import parse_date
from settings import DAILY_TASK_COUNT, DAILY_TASK_POOL


@dataclass(frozen=True)
class TaskSpec:
    id: str
    description: str
    event: str
    target: int
    reward: int
    game_id: str | None = None      # only events from this machine count
    distinct: bool = False          # count different keys instead of events
    available: bool = True

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class DailyTask:
    def __init__(self, spec, progress=0, claimed=False, seen=()):
        self.spec = spec
        self._seen = list(seen)             # distinct keys counted so far
        self._progress = min(spec.target, max(progress, len(self._seen)))
        self._claimed = claimed and self._progress >= spec.target

    @property
    def id(self):
        return self.spec.id

    @property
    def description(self):
        return self.spec.description

    @property
    def target(self):
        return self.spec.target

    @property
    def reward_tokens(self):
        return self.spec.reward

    @property
    def progress(self):
        return self._progress

    @property
    def completed(self):
        return self._progress >= self.spec.target

    @property
    def claimed(self):
        return self._claimed

    @property
    def claimable(self):
        return self.completed and not self._claimed

    def on_event(self, event, amount=1, key=None, game_id=None):
        """Count an event. Returns True if the task's progress changed."""
        spec = self.spec
        if self.completed or event != spec.event or (spec.game_id and spec.game_id != game_id):
            return False
        if spec.distinct:
            if key is None or key in self._seen:
                return False
            self._seen.append(key)
            amount = 1
        before = self._progress
        self._progress = min(spec.target, self._progress + amount)
        return self._progress != before

    def claim(self):
        """Returns the reward tokens the first time a finished task is claimed,
        else 0."""
        if not self.claimable:
            return 0
        self._claimed = True
        return self.spec.reward

    def to_dict(self):
        data = {"id": self.id, "progress": self._progress,
                "completed": self.completed, "claimed": self._claimed}
        if self.spec.distinct:
            data["seen"] = list(self._seen)
        return data


def _int(value, default=0):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default


class DailyTaskManager:
    def __init__(self, pool=DAILY_TASK_POOL, count=DAILY_TASK_COUNT, date_=None, tasks=()):
        self.pool = {spec.id: spec for spec in map(self._as_spec, pool)}
        self.count = count
        self.date = date_
        self.tasks = list(tasks)

    @staticmethod
    def _as_spec(entry):
        return entry if isinstance(entry, TaskSpec) else TaskSpec.from_dict(entry)

    # ------------------------------------------------------------ generation
    def ensure_current(self, today, rng=None):
        """Roll a new set of tasks if `today` is a later date than the current
        set (or there is none). Returns True if new tasks were generated."""
        if self.date is not None and self.tasks and today <= self.date:
            return False
        self.reset(today, rng)
        return True

    def reset(self, today, rng=None):
        """Replace the tasks with a fresh random set for `today`. Without an
        rng the picks depend only on the date, so they are repeatable."""
        rng = rng or random.Random(today.toordinal())
        offered = [s for s in self.pool.values() if s.available]
        self.tasks = [DailyTask(s) for s in rng.sample(offered, min(self.count, len(offered)))]
        self.date = today

    # ------------------------------------------------------------ progress
    def on_event(self, event, amount=1, key=None, game_id=None):
        """Feed an event to every task. Returns the tasks whose progress changed."""
        return [t for t in self.tasks if t.on_event(event, amount, key, game_id)]

    def get(self, task_id):
        return next((t for t in self.tasks if t.id == task_id), None)

    def claim(self, task_id):
        """Reward tokens for the task (0 if unknown, unfinished or claimed)."""
        task = self.get(task_id)
        return task.claim() if task else 0

    @property
    def claimable(self):
        return [t for t in self.tasks if t.claimable]

    # ------------------------------------------------------------ save data
    def to_dict(self):
        return {"date": self.date.isoformat() if self.date else None,
                "task_ids": [t.id for t in self.tasks],
                "tasks": [t.to_dict() for t in self.tasks]}

    @classmethod
    def from_dict(cls, data, **config):
        """Rebuild saved tasks. Entries for tasks no longer in the pool, and
        broken entries, are dropped; a set that ends up empty is regenerated
        by the next ensure_current()."""
        manager = cls(**config)
        data = data if isinstance(data, dict) else {}
        saved = data.get("tasks")
        for entry in saved if isinstance(saved, list) else []:
            spec = manager.pool.get(entry.get("id")) if isinstance(entry, dict) else None
            if spec is None or any(t.id == spec.id for t in manager.tasks):
                continue
            seen = entry.get("seen")
            seen = [k for k in seen if isinstance(k, str)] if isinstance(seen, list) else []
            manager.tasks.append(DailyTask(spec, _int(entry.get("progress")),
                                           entry.get("claimed") is True, seen))
        manager.date = parse_date(data.get("date")) if manager.tasks else None
        return manager
