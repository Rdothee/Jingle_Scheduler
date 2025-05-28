import datetime
import threading
import time

from playsound import playsound

from Jingle import Jingle


class MP3Scheduler:
    def __init__(self):
        self.scheduler_thread = None
        self.scheduled_jobs = []

    def play_mp3(self, path):
        print(f"Playing {path}")
        playsound(path)

    def schedule_mp3(self, jingle):
        scheduled_datetime = datetime.datetime.strptime(f"{jingle.date} {jingle.time_str}", "%Y-%m-%d %H:%M:%S")
        if scheduled_datetime <= datetime.datetime.now():
            print("Scheduled time has already passed. Skipping scheduling.")
            return
        job_info = {
            "date": jingle.date,
            "time_str": jingle.time_str,
            "path": jingle.path
        }
        self.scheduled_jobs.append(job_info)

    def start_scheduler(self):
        def job():
            while True:
                for job_info in self.scheduled_jobs:
                    scheduled_datetime = datetime.datetime.strptime(
                        f"{job_info['date']} {job_info['time_str']}", "%Y-%m-%d %H:%M:%S"
                    )
                    if datetime.datetime.now() >= scheduled_datetime:
                        print(f"Scheduled time has passed for {job_info['path']}")
                        self.play_mp3(job_info['path'])
                        self.scheduled_jobs.remove(job_info)
                time.sleep(1)

        self.scheduler_thread = threading.Thread(target=job)
        self.scheduler_thread.start()

    def stop_scheduler(self):
        if self.scheduler_thread:
            self.scheduler_thread.join()


