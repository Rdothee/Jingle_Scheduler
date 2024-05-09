import atexit
import time

import CsvReader
import Match
import Mp3Scheduler


class Main:
    jinglePath = "./resources/Jingles.csv"
    schedulePath = "./resources/Schedule.csv"
    matches = []
    scheduler = Mp3Scheduler.MP3Scheduler()

    def __init__(self):
        self.jingles = CsvReader.read_csv_without_headers(self.jinglePath)
        self.schedule = CsvReader.read_csv_without_headers(self.schedulePath)
        pass

    def run(self):
        # Main execution method
        atexit.register(self.cleanup_function)
        for startTime in self.schedule:
            match = Match.Match(startTime[0], self.jingles)
            match.create_jingles()
            self.matches.append(match)
            match.print_schedule()

        self.ScheduleJingles()
        self.keepProgramAlive()
        pass

    def ScheduleJingles(self):
        for match in self.matches:
            for jingle in match.jingles:
                self.scheduler.schedule_mp3(jingle)
        self.scheduler.start_scheduler()
        pass

    def cleanup_function(self):
        self.scheduler.stop_scheduler()
        print("Cleanup function executed.")
        return

    # Register the cleanup function

    def keepProgramAlive(self):
        print("Running...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt detected. Exiting program...")



if __name__ == "__main__":
    main = Main()
    main.run()
