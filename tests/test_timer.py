import pytest
from coffemodoro.core.timer import Timer, TimerState, TimerMode

def make_timer(focus=25, short=5, long=15, sessions_before_long=4):
    ticks = []
    completions = []
    t = Timer(
        focus_duration=focus * 60,
        short_break=short * 60,
        long_break=long * 60,
        sessions_before_long=sessions_before_long,
        on_tick=lambda elapsed, total: ticks.append((elapsed, total)),
        on_complete=lambda mode, count: completions.append((mode, count)),
    )
    return t, ticks, completions

def test_initial_state():
    t, _, _ = make_timer()
    assert t.state == TimerState.IDLE
    assert t.mode == TimerMode.FOCUS
    assert t.elapsed_seconds == 0
    assert t.progress == 0.0

def test_start_changes_state_to_running():
    t, _, _ = make_timer()
    t.start()
    assert t.state == TimerState.RUNNING

def test_tick_increments_elapsed():
    t, ticks, _ = make_timer()
    t.start()
    t.tick()
    assert t.elapsed_seconds == 1
    assert len(ticks) == 1
    assert ticks[0] == (1, 25 * 60)

def test_pause_stops_ticking():
    t, _, _ = make_timer()
    t.start()
    t.pause()
    assert t.state == TimerState.PAUSED
    t.tick()  # should have no effect
    assert t.elapsed_seconds == 0

def test_resume_after_pause():
    t, _, _ = make_timer()
    t.start()
    t.pause()
    t.resume()
    assert t.state == TimerState.RUNNING
    t.tick()
    assert t.elapsed_seconds == 1

def test_reset_returns_to_idle():
    t, _, _ = make_timer()
    t.start()
    t.tick()
    t.reset()
    assert t.state == TimerState.IDLE
    assert t.elapsed_seconds == 0

def test_completion_fires_callback():
    t, _, completions = make_timer(focus=1)  # 60 seconds
    t.start()
    for _ in range(60):
        t.tick()
    assert len(completions) == 1
    assert completions[0][0] == TimerMode.FOCUS

def test_after_focus_completes_mode_is_short_break():
    t, _, _ = make_timer(focus=1)
    t.start()
    for _ in range(60):
        t.tick()
    assert t.mode == TimerMode.SHORT_BREAK
    assert t.state == TimerState.IDLE

def test_after_4_focus_sessions_long_break():
    t, _, _ = make_timer(focus=1, short=1, sessions_before_long=4)
    for i in range(4):
        t.start()
        for _ in range(60):
            t.tick()
        if i < 3:  # skip only the first 3 short breaks, not the long break
            t.skip()
    assert t.mode == TimerMode.LONG_BREAK

def test_skip_long_break_returns_to_focus():
    t, _, _ = make_timer(focus=1, short=1, sessions_before_long=4)
    # complete 4 focus sessions to trigger long break
    for i in range(4):
        t.start()
        for _ in range(60):
            t.tick()
        if i < 3:
            t.skip()
    assert t.mode == TimerMode.LONG_BREAK
    t.skip()  # skip the long break
    assert t.mode == TimerMode.FOCUS

def test_skip_advances_to_next_mode():
    t, _, _ = make_timer()
    t.skip()
    assert t.mode == TimerMode.SHORT_BREAK

def test_progress():
    t, _, _ = make_timer(focus=1)
    t.start()
    for _ in range(30):
        t.tick()
    assert abs(t.progress - 0.5) < 0.01

def test_remaining_seconds():
    t, _, _ = make_timer(focus=1)
    t.start()
    t.tick()
    assert t.remaining_seconds == 59

def test_update_durations_resets_elapsed():
    t, _, _ = make_timer(focus=5)
    t.start()
    for _ in range(100):
        t.tick()
    t.update_durations(focus=1 * 60, short=5 * 60, long=15 * 60, sessions_before_long=4)
    assert t.elapsed_seconds == 0
    assert t.state == TimerState.IDLE

def test_update_durations_applies_new_total():
    t, _, _ = make_timer(focus=25)
    t.update_durations(focus=10 * 60, short=5 * 60, long=15 * 60, sessions_before_long=4)
    assert t.total_seconds == 10 * 60
