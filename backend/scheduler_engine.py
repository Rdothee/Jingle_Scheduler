"""
scheduler_engine.py

Refactored audio scheduling engine with:
  - Pause / resume support
  - Per-jingle state tracking (PENDING, PLAYING, PLAYED, SKIPPED)
  - Callback hooks so the UI can react to state changes
  - Thread-safe job list
"""

import datetime
import threading
import time
from enum import Enum

try:
    from playsound import playsound
except ImportError:
    playsound = None


class JingleStatus(Enum):
    PENDING = "PENDING"
    PLAYING = "PLAYING"
    PLAYED  = "PLAYED"
    SKIPPED = "SKIPPED"


class ScheduledJob:
    """Represents one jingle that has been queued for playback."""

    def __init__(self, jingle):
        self.jingle = jingle                  # Jingle model object
        self.scheduled_dt: datetime.datetime = datetime.datetime.strptime(
            f"{jingle.date} {jingle.time_str}", "%Y-%m-%d %H:%M:%S"
        )
        self.status: JingleStatus = JingleStatus.PENDING

    # Convenience accessors
    @property
    def path(self) -> str:
        return self.jingle.path


class SchedulerEngine:
    """
    Manages a list of ScheduledJobs and fires them at the right wall-clock time.

    Events / callbacks
    ------------------
    on_status_change(job: ScheduledJob)
        Called on the engine's background thread whenever a job's status changes.
        Consumers should use `root.after(0, ...)` or a thread-safe queue to
        bridge back to the UI thread.
    on_tick()
        Called every second by the background thread (useful for updating a
        live clock or progress bar).
    """

    def __init__(self):
        self._jobs: list[ScheduledJob] = []
        self._lock = threading.Lock()

        self._running = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()          # not paused initially → event is "set"

        self._thread: threading.Thread | None = None
        self._current_job: ScheduledJob | None = None

        # Callbacks — assign from the UI layer
        self.on_status_change = None   # callable(job) | None
        self.on_tick = None            # callable()    | None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_job(self, jingle) -> ScheduledJob:
        """Add a jingle to the queue.  Returns the ScheduledJob wrapper."""
        job = ScheduledJob(jingle)
        with self._lock:
            self._jobs.append(job)
        return job

    def clear_jobs(self):
        """Remove all pending jobs (does NOT stop a currently-playing file)."""
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status == JingleStatus.PLAYING]

    def start(self):
        """Start the background scheduler thread."""
        if self._running:
            return
        self._running = True
        self._paused = False
        self._pause_event.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduler thread gracefully."""
        self._running = False
        self._pause_event.set()   # unblock if paused so the thread can exit

    def pause(self):
        """Pause: upcoming jingles will not fire until resumed."""
        self._paused = True
        self._pause_event.clear()

    def resume(self):
        """Resume from pause."""
        self._paused = False
        self._pause_event.set()

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_running(self) -> bool:
        return self._running

    def get_jobs(self) -> list[ScheduledJob]:
        """Return a snapshot of all jobs (thread-safe)."""
        with self._lock:
            return list(self._jobs)

    @property
    def current_job(self) -> ScheduledJob | None:
        return self._current_job

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self):
        while self._running:
            # Block here when paused; unblocks when resume() is called
            self._pause_event.wait()

            if not self._running:
                break

            now = datetime.datetime.now()

            with self._lock:
                pending = [j for j in self._jobs if j.status == JingleStatus.PENDING]

            for job in pending:
                if job.scheduled_dt <= now:
                    if self._paused:
                        # Mark as skipped only if far in the past (> 30 s)
                        if (now - job.scheduled_dt).total_seconds() > 30:
                            self._set_status(job, JingleStatus.SKIPPED)
                    else:
                        self._play_job(job)

            if self.on_tick:
                try:
                    self.on_tick()
                except Exception:
                    pass

            time.sleep(1)

    def _play_job(self, job: ScheduledJob):
        self._current_job = job
        self._set_status(job, JingleStatus.PLAYING)

        def _play():
            try:
                if playsound:
                    playsound(job.path)
            except Exception as e:
                print(f"[SchedulerEngine] Playback error: {e}")
            finally:
                if job.status == JingleStatus.PLAYING:
                    self._set_status(job, JingleStatus.PLAYED)
                if self._current_job is job:
                    self._current_job = None

        t = threading.Thread(target=_play, daemon=True)
        t.start()

    def _set_status(self, job: ScheduledJob, status: JingleStatus):
        job.status = status
        job.jingle.status = status.value  # keep Jingle model in sync
        if self.on_status_change:
            try:
                self.on_status_change(job)
            except Exception:
                pass
