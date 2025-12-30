from service.enum_typing import ErrorType


class DetectResult:
    def __init__(self, error_type, tag, old, new, start, end, notice):
        self.error_type = error_type
        self.tag = tag
        self.old = old
        self.new = new
        self.start = start
        self.end = end
        self.notice = notice

    def __dict__(self):
        return {
            'type': self.error_type,
            'tag': self.tag,
            'old': self.old,
            'new': self.new,
            'start': self.start,
            'end': self.end,
            'notice': self.notice
        }

    def to_dict(self):
        return self.__dict__()

    def __str__(self):
        return str(self.__dict__())

    def __repr__(self):
        return f"DetectResult: {self.__dict__()}"


class BaseDetector:

    error_type = ErrorType



