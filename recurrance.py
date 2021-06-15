import dateutil.rrule as dr
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU
import dateutil.parser as dp
import dateutil.relativedelta as drel


class Recurrance:
    def __init__(self, startDate, monthDay=None, weekNum=None, endBy=None, interval=None, numOfOccurances=None, weekDays=None, daysOfWeek=None):
        self.startDate = startDate
        self.endBy = endBy
        self.interval = interval
        self.numOfOccurances = numOfOccurances
        self.daysOfWeek = daysOfWeek
        self.monthDay = monthDay
        self.weekNum = weekNum  # firts, second, third, forth, or las of the months

    def daily(self):
        dates = dr.rrule(dr.DAILY, dtstart=self.startDate, until=self.endBy,
                         interval=self.interval, count=self.numOfOccurances)
        return dates

    def weekdays(self):
        if self.numOfOccurances:
            dates = dr.rrule(dr.WEEKLY, byweekday=range(
                5), dtstart=self.startDate, count=self.numOfOccurances)
        else:
            dates = dr.rrule(dr.WEEKLY, byweekday=range(
                5), dtstart=self.startDate, until=self.endBy)
        return dates

    def weekly(self):
        if self.numOfOccurances:
            dates = dr.rrule(dr.WEEKLY, byweekday=self.daysOfWeek, dtstart=self.startDate,
                             interval=self.interval, count=self.numOfOccurances)
        else:
            dates = dr.rrule(dr.WEEKLY, byweekday=self.daysOfWeek, dtstart=self.startDate,
                             interval=self.interval, until=self.endBy)
        return dates

    def monthlyDayNum(self):
        if self.numOfOccurances:
            dates = dr.rrule(dr.MONTHLY, bymonthday=self.monthDay,
                             dtstart=self.startDate, interval=self.interval, count=self.numOfOccurances)
        else:
            dates = dr.rrule(dr.MONTHLY, bymonthday=self.monthDay,
                             dtstart=self.startDate, interval=self.interval, until=self.endBy)
        return dates

    def monthlyDayOfWeek(self):
        if self.numOfOccurances:
            dates = dr.rrule(dr.MONTHLY, byweekday=self.daysOfWeek(self.weekNum),
                             dtstart=self.startDate, interval=self.interval, count=self.numOfOccurances)
        else:
            dates = dr.rrule(dr.MONTHLY, byweekday=self.daysOfWeek(self.weekNum),
                             dtstart=self.startDate, interval=self.interval, until=self.endBy)

        return dates
