import threading
from pathlib import Path

from core.conversion_engine import ConversionEngine
from core.progress_manager import ProgressManager


class ConversionWorker(threading.Thread):

    def __init__(
        self,
        files,
        output_dir,
        event_queue,
        overwrite_existing=False,
        output_format="PDF",
        output_formats=None
    ):
        super().__init__(daemon=True)

        self.files = [Path(file).resolve() for file in files]
        self.output_dir = Path(output_dir).resolve()
        self.event_queue = event_queue
        self.overwrite_existing = overwrite_existing
        self.output_format = str(output_format).upper()
        self.output_formats = {
            str(Path(path).resolve()): str(fmt).upper()
            for path, fmt in (output_formats or {}).items()
        }

        self.cancel_event = threading.Event()
        self.progress = ProgressManager()
        self.progress.add_jobs(self.files)

    def cancel(self):
        self.cancel_event.set()
        self.event_queue.put({"type": "cancel_requested"})

    def send_event(self, event_type, **data):
        self.event_queue.put({"type": event_type, **data})

    def run(self):
        successful = 0
        failed = 0

        try:
            engine = ConversionEngine()

            self.send_event(
                "started",
                total=self.progress.total
            )

            for file_path in self.files:
                if self.cancel_event.is_set():
                    self.mark_remaining_cancelled()
                    break

                self.progress.start_job(file_path)

                self.send_event(
                    "file_started",
                    file=str(file_path)
                )

                try:
                    selected_format = self.output_formats.get(
                        str(file_path),
                        self.output_format
                    )

                    result = engine.convert(
                        file_path,
                        self.output_dir,
                        output_format=selected_format,
                        overwrite=self.overwrite_existing
                    )

                    self.progress.complete_job(file_path)
                    successful += 1

                    self.send_event(
                        "file_completed",
                        file=str(file_path),
                        output=str(result)
                    )

                except Exception as error:
                    self.progress.fail_job(file_path, str(error))
                    failed += 1

                    self.send_event(
                        "file_failed",
                        file=str(file_path),
                        error=str(error)
                    )

                self.send_progress()

                if self.cancel_event.is_set():
                    self.mark_remaining_cancelled()
                    break

            snapshot = self.progress.get_snapshot()

            self.send_event(
                "finished",
                successful=successful,
                failed=failed,
                cancelled=snapshot["cancelled"],
                total=self.progress.total,
                progress=snapshot["progress_percent"],
                was_cancelled=self.cancel_event.is_set()
            )

        except Exception as error:
            self.send_event(
                "worker_error",
                error=str(error)
            )

    def mark_remaining_cancelled(self):
        for file_path in self.files:
            job = self.progress._get_job(file_path)

            if job["status"] == "pending":
                self.progress.start_job(file_path)
                self.progress.cancel_job(file_path)

                self.send_event(
                    "file_cancelled",
                    file=str(file_path)
                )

                self.send_progress()

    def send_progress(self):
        self.send_event(
            "progress",
            **self.progress.get_snapshot()
        )
