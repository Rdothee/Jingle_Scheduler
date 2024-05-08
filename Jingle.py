class Jingle:
    def __init__(self, path, date, time_str):
        self._path = path
        self._date = date
        self._time_str = time_str

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        self._date = value

    @property
    def time_str(self):
        return self._time_str

    @time_str.setter
    def time_str(self, value):
        self._time_str = value
