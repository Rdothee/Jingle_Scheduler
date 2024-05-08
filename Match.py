
import datetime
import time
from Jingle import Jingle
class Match:
    def __init__(self, match_datetime, jingles_matrix):
        self.match_datetime = match_datetime
        self.jingles_matrix = jingles_matrix
        self.jingles = []

    def create_jingles(self):
        for jingle_info in self.jingles_matrix:
            path, offset_minutes = jingle_info
            jingle_datetime = self.match_datetime - datetime.timedelta(minutes=offset_minutes)
            jingle_date = jingle_datetime.strftime("%Y-%m-%d")
            jingle_time_str = jingle_datetime.strftime("%H:%M:%S")
            jingle = Jingle(path, jingle_date, jingle_time_str)
            self.jingles.append(jingle)

    def print_schedule(self):
        print(f"Match Date: {self.match_datetime}")
        for i, jingle in enumerate(self.jingles, 1):
            print(f"Jingle {i}: Path={jingle.path}, Scheduled Date={jingle.date}, Scheduled Time={jingle.time_str}")

