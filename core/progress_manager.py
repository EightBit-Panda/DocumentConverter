
from pathlib import Path
from datetime import datetime


class ProgressManager:
    """
    Tracks document conversion jobs and their progress.
    """

    VALID_STATUSES = {
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled"
    }

    TERMINAL_STATUSES = {
        "completed",
        "failed",
        "cancelled"
    }

    def __init__(self):

        self.jobs = {}
        self.started_at = None
        self.finished_at = None

    # ==============================================
    # ADD JOBS
    # ==============================================

    def add_jobs(self, files):

        if self.jobs:
            raise RuntimeError(
                "Progress manager already contains jobs. "
                "Reset it before starting a new batch."
            )

        for file in files:

            path = Path(file).resolve()
            job_id = str(path)

            if job_id in self.jobs:
                continue

            self.jobs[job_id] = {
                "file": path,
                "status": "pending",
                "error": None,
                "started_at": None,
                "finished_at": None
            }

        self.started_at = None
        self.finished_at = None

        return len(self.jobs)

    # ==============================================
    # START JOB
    # ==============================================

    def start_job(self, file):

        job = self._get_job(file)

        if job["status"] != "pending":
            raise RuntimeError(
                "Only pending jobs can be started."
            )

        job["status"] = "running"
        job["started_at"] = datetime.now()

        if self.started_at is None:
            self.started_at = datetime.now()

    # ==============================================
    # COMPLETE JOB
    # ==============================================

    def complete_job(self, file):

        self._finish_job(file, "completed")

    # ==============================================
    # FAIL JOB
    # ==============================================

    def fail_job(self, file, error):

        self._finish_job(
            file,
            "failed",
            error=str(error)
        )

    # ==============================================
    # CANCEL JOB
    # ==============================================

    def cancel_job(self, file):

        self._finish_job(file, "cancelled")

    # ==============================================
    # FINISH JOB
    # ==============================================

    def _finish_job(self, file, status, error=None):

        if status not in self.TERMINAL_STATUSES:
            raise ValueError("Invalid final status.")

        job = self._get_job(file)

        if job["status"] != "running":
            raise RuntimeError(
                "Only running jobs can be completed, "
                "failed or cancelled."
            )

        job["status"] = status
        job["error"] = error
        job["finished_at"] = datetime.now()

        if self.is_finished:
            self.finished_at = datetime.now()

    # ==============================================
    # GET JOB
    # ==============================================

    def _get_job(self, file):

        job_id = str(Path(file).resolve())

        if job_id not in self.jobs:
            raise KeyError(
                f"Job not found: {job_id}"
            )

        return self.jobs[job_id]

    # ==============================================
    # COUNTERS
    # ==============================================

    @property
    def total(self):

        return len(self.jobs)

    @property
    def completed(self):

        return self.count_status("completed")

    @property
    def failed(self):

        return self.count_status("failed")

    @property
    def cancelled(self):

        return self.count_status("cancelled")

    @property
    def pending(self):

        return self.count_status("pending")

    @property
    def running(self):

        return self.count_status("running")

    @property
    def remaining(self):

        return self.pending + self.running

    @property
    def processed(self):

        return (
            self.completed
            + self.failed
            + self.cancelled
        )

    # ==============================================
    # PROGRESS
    # ==============================================

    @property
    def progress_percent(self):

        if self.total == 0:
            return 0

        return round(
            (self.processed / self.total) * 100,
            1
        )

    # ==============================================
    # FINISHED CHECK
    # ==============================================

    @property
    def is_finished(self):

        return (
            self.total > 0
            and self.processed == self.total
        )

    # ==============================================
    # STATUS COUNTER
    # ==============================================

    def count_status(self, status):

        if status not in self.VALID_STATUSES:
            raise ValueError("Unknown job status.")

        return sum(
            1
            for job in self.jobs.values()
            if job["status"] == status
        )

    # ==============================================
    # CURRENT JOB
    # ==============================================

    @property
    def current_file(self):

        for job in self.jobs.values():

            if job["status"] == "running":
                return job["file"]

        return None

    # ==============================================
    # STATUS SNAPSHOT
    # ==============================================

    def get_snapshot(self):

        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "pending": self.pending,
            "running": self.running,
            "remaining": self.remaining,
            "processed": self.processed,
            "progress_percent": self.progress_percent,
            "is_finished": self.is_finished,
            "current_file": (
                str(self.current_file)
                if self.current_file
                else None
            )
        }

    # ==============================================
    # RESET
    # ==============================================

    def reset(self):

        self.jobs.clear()
        self.started_at = None
        self.finished_at = None
