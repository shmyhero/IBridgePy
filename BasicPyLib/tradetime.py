import datetime
import pytz

from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, nearest_workday, USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, USLaborDay, USThanksgivingDay


class USTradingCalendar(AbstractHolidayCalendar):
    rules = [
        Holiday('NewYearsDay', month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday('USIndependenceDay', month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday('Christmas', month=12, day=25, observance=nearest_workday)
    ]


class TradeTime(object):

    _holidays_cache = {}

    def __init__(self):
        pass

    @staticmethod
    def get_trading_close_holidays(year):
        inst = USTradingCalendar()
        return inst.holidays(datetime.datetime(year - 1, 12, 31), datetime.datetime(year, 12, 31))

    @staticmethod
    def is_special_weekday(date, month, week_count, weekday_index):
        if date.month == month and date.weekday() == weekday_index and week_count*7 < date.day < (week_count+1)*7:
            return True

    @staticmethod
    def is_trade_day(date):
        trading_close_holidays = TradeTime._holidays_cache.get(date.year)
        if trading_close_holidays is None:
            trading_close_holidays = TradeTime.get_trading_close_holidays(date.year)
            TradeTime._holidays_cache[date.year] = trading_close_holidays
        if date.weekday() >= 5:
            return False
        elif date in trading_close_holidays:
            return False
        else:
            return True

    @staticmethod
    def get_half_trade_dates(year):
        '''
        there are 3 special days for half day trading, they are:
        the date before chirstmas day,
        the date before independent day,
        the date after thanks giving day. Oct, the 4th Thursday
        :param nydate:
        :return:
        '''

        half_trade_dates = []

        independent_before_date = datetime.date(year, 7, 3)
        if independent_before_date.weekday() <= 5:
            half_trade_dates.append(independent_before_date)

        nov1 = datetime.date(year, 11, 1)
        delta = 3 - nov1.weekday()
        if delta < 0:
            delta += 7
        thanksgiving_after_date = datetime.date(year, 11, 1 + delta + 3*7 + 1)
        half_trade_dates.append(thanksgiving_after_date)

        christmas_eve = datetime.date(year, 12, 24)
        if christmas_eve.weekday() <= 5:
            half_trade_dates.append(christmas_eve)

        return half_trade_dates


    @staticmethod
    def is_half_trade_day(nydate):
        half_trade_dates = list(TradeTime.get_half_trade_dates(nydate.year))
        return nydate in half_trade_dates

    @staticmethod
    def is_market_open():
        now = datetime.datetime.now(tz=pytz.timezone('US/Eastern'))
        if TradeTime.is_trade_day(now.date()):
            if TradeTime.is_half_trade_day(now.date()):
                end_hour = 13
            else:
                end_hour = 16
            minutes = now.hour * 60 + now.minute
            if minutes >= 9 * 60 + 30 and minutes < end_hour * 60:
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def get_latest_trade_date():
        for i in range(10):
            trade_date = datetime.datetime.today() - datetime.timedelta(days=i+1)
            if TradeTime.is_trade_day(trade_date):
                return trade_date.date()

if __name__ == '__main__':
    print TradeTime.get_trading_close_holidays(2017)
    print TradeTime.get_half_trade_dates(2015)
    print TradeTime.is_trade_day(datetime.date(2017, 12, 25))
    print TradeTime.is_trade_day(datetime.date(2017, 9, 1))
    print TradeTime.is_trade_day(datetime.date(2017, 9, 4))
    print TradeTime.is_half_trade_day(datetime.date(2017, 7, 3))
    print TradeTime.is_market_open()
    print TradeTime.get_latest_trade_date()
