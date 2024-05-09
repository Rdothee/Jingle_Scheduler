from datetime import datetime, timedelta
from Jingle import Jingle


class Match:
    def __init__(self, schedule, jingles):
        self.match_datetime = datetime.strptime(schedule, "%Y-%m-%d %H:%M:%S")
        self.jinglesData = jingles
        self.jingles = []

    def create_jingles(self):
        for jingle_info in self.jinglesData:
            path, offset_minutes = jingle_info
            jingle_datetime = self.match_datetime + timedelta(minutes=int(offset_minutes))
            jingle_date = jingle_datetime.strftime("%Y-%m-%d")
            jingle_time_str = jingle_datetime.strftime("%H:%M:%S")
            jingle = Jingle(path, jingle_date, jingle_time_str)
            self.jingles.append(jingle)

    def print_schedule(self):
        print(f"Match Date: {self.match_datetime}")
        for i, jingle in enumerate(self.jingles, 1):
            print(f"Jingle {i}: Path={jingle.path}, Scheduled Date={jingle.date}, Scheduled Time={jingle.time_str}")
