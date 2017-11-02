# -*- coding: utf-8 -*-
"""
Created on Fri Jun  2 17:45:12 2017

@author: IBridgePy@gmail.com
"""

'''
from pandas.tseries.holiday import get_calendar, HolidayCalendarFactory, GoodFriday
from datetime import datetime

cal = get_calendar('USFederalHolidayCalendar')  # Create calendar instance
print (cal.rules)
cal.rules.pop(7)                                # Remove Veteran's Day rule
cal.rules.pop(6)                                # Remove Columbus Day rule
tradingCal = HolidayCalendarFactory('TradingCalendar', cal, GoodFriday)
print (tradingCal.rules)

#new instance of class
cal1 = tradingCal()

print (cal1.holidays(datetime(2014, 12, 31), datetime(2016, 12, 31)))
'''

import datetime as dt
import pandas as pd

from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, nearest_workday, \
    USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, \
    USLaborDay, USThanksgivingDay
from pandas.tseries.offsets import MonthEnd


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


def get_trading_close_holidays(startDay, endDay):
    # startDay and endDay are inclusive
    # if startDay or endDay is a holiday, it will show up in the result
    inst = USTradingCalendar()
    return inst.holidays(startDay, endDay)

def trading_day(day):
    '''
    return True if day is a trading day
    '''
    # Monday weekday=0
    # Sunday weekday=6
    #print (day)
    if day.weekday()>=5: # weekends are not trading day
        return False
    # check if day->day+1 has holidays and if day == holiday
    return not pd.Timestamp(day) in get_trading_close_holidays(day, day+dt.timedelta(days=1)) 

def nth_trading_day_of_week(aDay):
    if type(aDay)==dt.datetime:
        aDay=aDay.date()
    if not trading_day(aDay):
        return 'marketClose' # day is not a trading day
    #if day is a trading day, return Nth trading day of the week
    # 0 is 1st trading day of week
    tmp=aDay.weekday()
    start=aDay-dt.timedelta(days=tmp)
    end=start+dt.timedelta(days=4)
    for ct in get_trading_close_holidays(start, end):
        if ct<pd.Timestamp(aDay):
            tmp-=1
    sm=count_trading_days_in_a_week(aDay)
    return tmp,-(sm-tmp)
 
def nth_trading_day_of_month(aDay):
    if type(aDay) == dt.datetime:
        aDay = aDay.date()
    if not trading_day(aDay):
        return 'marketClose' # day is not a trading day
    #if day is a trading day, return Nth trading day of the month
    # 0 is 1st trading day of month
    tmp = aDay.day
    ans = tmp - 1
    start = aDay.replace(day = 1)
    i = 0
    while i < tmp:
        if not trading_day(start + dt.timedelta(days = i)):
            ans -= 1
        i += 1
    sm = count_trading_days_in_a_month(aDay)
    return ans,-(sm - ans)

def count_trading_days(startDay, endDay):
    '''
    include startDay and endDay
    '''
    ans=0
    i=0
    tmp=startDay+dt.timedelta(days=i)
    while tmp<=endDay:
        if trading_day(startDay+dt.timedelta(days=i)):
            ans+=1
        i+=1
        tmp=startDay+dt.timedelta(days=i)
    return ans

def count_trading_days_in_a_month(aDay):
    #tmp=(aDay+MonthEnd(1)).date() # change pd.TimeStampe to dt.date
    next_month = aDay.replace(day=28) + dt.timedelta(days=4)  # this will never fail
    tmp = next_month - dt.timedelta(days=next_month.day)
    return count_trading_days(aDay.replace(day=1), tmp )

def count_trading_days_in_a_week(aDay):
    # Monday weekday=0
    # Sunday weekday=6
    if type(aDay)==dt.datetime:
        aDay=aDay.date()
    tmp=aDay.weekday()
    start=aDay-dt.timedelta(days=tmp)
    end=start+dt.timedelta(days=4)
    return count_trading_days(start,end)

def get_params_of_a_daytime(dayTime):
    return (nth_trading_day_of_month(dayTime),
            nth_trading_day_of_week(dayTime),
            dayTime.hour,
            dayTime.minute)

def switch_goBack(startTime, endTime):
    if startTime>=endTime:
        print(__name__+'::switch_time: EXIT, startTime >= endTime')
        print ('startTime=',startTime)
        print ('endTime=', endTime)
        exit()
    #return str((endTime-startTime).days+1)+' D'
    return str(count_trading_days(startTime, endTime))+' D'

if __name__ == '__main__':
    print ('start')
    #print(get_trading_close_holidays(dt.date(2017,4,1), dt.date(2017,4,30)))
    #print(trading_day(dt.date(2017,9,1)))
    print (nth_trading_day_of_week(dt.date(2017,9,1)))
    #print (nth_trading_day_of_month(dt.date(2017,9,1)))
    #print (count_trading_days(dt.date(2017,5,1), dt.date(2017,5,31)))
    #print (dt.date(2017,4,13)+MonthEnd(1))
    #print (count_trading_days(dt.date(2017,4,1), dt.date(2017,4,13)+MonthEnd(1)))
    #print (count_trading_days_in_a_month(dt.date(2017,5,13)))
    #print (count_trading_days_in_a_week(dt.date(2017,6,1)))
    #print (get_params_of_a_daytime(dt.datetime.now()))
    #print (get_params_of_a_daytime(dt.datetime(2017,5,30,12,30)))