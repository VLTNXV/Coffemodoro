from enum import Enum, auto
from typing import Callable


class TimerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()


class TimerMode(Enum):
    FOCUS = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()


class Timer:
    def __init__(
        self,
        focus_duration: int,
        short_break: int,
        long_break: int,
        sessions_before_long: int,
        on_tick: Callable[[int, int], None],
        on_complete: Callable[["TimerMode", int], None],
    ):
        self._focus_duration = focus_duration
        self._short_break = short_break
        self._long_break = long_break
        self._sessions_before_long = sessions_before_long
        self._on_tick = on_tick
        self._on_complete = on_complete

        self.state = TimerState.IDLE
        self.mode = TimerMode.FOCUS
        self.elapsed_seconds = 0
        self.sessions_completed = 0

    @property
    def total_seconds(self) -> int:
        return {
            TimerMode.FOCUS: self._focus_duration,
            TimerMode.SHORT_BREAK: self._short_break,
            TimerMode.LONG_BREAK: self._long_break,
        }[self.mode]

    @property
    def remaining_seconds(self) -> int:
        return self.total_seconds - self.elapsed_seconds

    @property
    def progress(self) -> float:
        if self.total_seconds == 0:
            return 0.0
        return self.elapsed_seconds / self.total_seconds

    def start(self):
        if self.state == TimerState.IDLE:
            self.state = TimerState.RUNNING

    def pause(self):
        if self.state == TimerState.RUNNING:
            self.state = TimerState.PAUSED

    def resume(self):
        if self.state == TimerState.PAUSED:
            self.state = TimerState.RUNNING

    def reset(self):
        self.state = TimerState.IDLE
        self.elapsed_seconds = 0

    def full_reset(self):
        self.state = TimerState.IDLE
        self.elapsed_seconds = 0
        self.sessions_completed = 0
        self.mode = TimerMode.FOCUS

    def skip(self):
        self._advance_mode()
        self.state = TimerState.IDLE
        self.elapsed_seconds = 0

    def tick(self):
        if self.state != TimerState.RUNNING:
            return
        self.elapsed_seconds += 1
        self._on_tick(self.elapsed_seconds, self.total_seconds)
        if self.elapsed_seconds >= self.total_seconds:
            self._complete()

    def _complete(self):
        completed_mode = self.mode
        if completed_mode == TimerMode.FOCUS:
            self.sessions_completed += 1
        self._advance_mode()
        self.state = TimerState.IDLE
        self.elapsed_seconds = 0
        self._on_complete(completed_mode, self.sessions_completed)

    def _advance_mode(self):
        if self.mode == TimerMode.FOCUS:
            if self.sessions_completed % self._sessions_before_long == 0 and self.sessions_completed > 0:
                self.mode = TimerMode.LONG_BREAK
            else:
                self.mode = TimerMode.SHORT_BREAK
        else:
            self.mode = TimerMode.FOCUS

    def update_durations(self, focus: int, short: int, long: int, sessions_before_long: int):
        self._focus_duration = focus
        self._short_break = short
        self._long_break = long
        self._sessions_before_long = sessions_before_long
        self.elapsed_seconds = 0
        self.state = TimerState.IDLE
