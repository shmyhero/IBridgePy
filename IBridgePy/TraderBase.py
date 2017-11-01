
import datetime as dt
import time, pytz
import pandas as pd
import BasicPyLib.simpleLogger as simpleLogger
from IBridgePy.quantopian import DataClass, ContextClass,QDataClass, ReqData
from IBridgePy.IBAccountManager import IBAccountManager
from IBridgePy.quantopian import calendars,time_rules
from BasicPyLib.handle_calendar import nth_trading_day_of_month,nth_trading_day_of_week


class Trader(IBAccountManager):
    """
    TickTraders are IBAccountManager too, so TickTraders inherits from IBAccountManager.
    """
    
    def setup_trader(self,
                    accountCode='All',
                    logLevel='INFO',
                    showTimeZone='US/Eastern',
                    maxSaveTime=1800,
                    waitForFeedbackinSeconds=30,
                    repeat=3,
                    repBarFreq=1,
                    handle_data_quantopian=None, # a function name is passed in.
                    initialize_quantopian=None, # a function name is passed in.
                    before_trading_start_quantopian=None): #optical function

        """
        initialize the IBAccountManager. We don't do __init__ here because we don't
        want to overwrite parent class IBCpp.IBClient's __init__ function
        stime: IB server time when it is first received. localTime is the local
        computer time when first IB server time is received. The following IB 
        server time is simulated by stime,localTime and dt.datetime.now()
        maxSaveTime: max timeframe to be saved in price_size_last_matrix for TickTrader

        """ 
        self.versionNumber = 2.20171016
        self.accountCode=accountCode
        self.context = ContextClass(accountCode) 
        self.qData=None          
        self.logLevel=logLevel
        self.showTimeZone=pytz.timezone(showTimeZone)
        self.maxSaveTime=maxSaveTime
        self.repBarFreq=repBarFreq 
        self.waitForFeedbackinSeconds=waitForFeedbackinSeconds
        self.repeat=repeat
        
        self.initialize_quantopian=initialize_quantopian
        if not handle_data_quantopian:
            self.handle_data_quantopian = (lambda x, y: None)
        else:
            self.handle_data_quantopian=handle_data_quantopian
        self.before_trading_start_quantopian=before_trading_start_quantopian
        
        # a flag to decide if display_all() should work
        # in test_run mode, tester will request historical data first
        # in this case, there is no need to display account info.
        self.displayFlag=True

        # in the run_like_quantopian mode
        # the system should use Easter timezone as the system time
        # self.sysTimeZone will be used for this purpose
        self.sysTimeZone=pytz.timezone('US/Eastern') 

    
        # record server UTC time and the local time 
        # when the first server time comes in
        # when the current server time is needed, used dt.datetime.now()
        # to calculate
        self.recordedServerUTCtime=None # float, utc number
        self.recordedLocalTime = None # a datetime, without tzinfo
        
        self.stime_previous=None
            
        self.nextId = 1         # nextValidId, all request will use the same series
                
        self.scheduledFunctionList=[]  # record all of user scheduled function conditions
        self.runMode = None        # runMode = 'test_run', =None in other cases
        self.runToday = True        # run_like_quantopian, at the beginning of a day
                                    # check if follow date_rules, if True, run today, else, not run today

        # record all realTimeRequests to avoid repeat calls 
        self.realTimePriceRequestedList={}

        # MarketMangerBase will monitor it to stop
        # False is want to run
        self.wantToEnd=False
        self.runUntilResults=None # in run_until mode, function results will be delivered back here.

        self.realtimeBarCount=0
        self.realtimeBarTime=None #MarketManagerBase use it to calculate the starting point

        # these two param are used in quantopian mode
        # For schedule function
        # They will be put in a value at the beginning of everyday
        self.monthDay= None
        self.weekDay=None
        
        
        #a Flag to tell if hist data has come in or request_hist has some error
        # set it to False when submit request
        # set it to True after received 1st hist line
        # it will be turned on after connection is established.
        # it will be turned off after errorId=1100
        self.receivedHistFlag=False
                
        # a flag to show if the connection between IB Gateway/TWS and IB serve
        # is good or not        
        # The most import usage is to ignor the connection check between 
        # IBridgePy and IB Gateway/TWS
        self.connectionGatewayToServer=False
        
        ############ for runMode=='test_run'
        
        # In the test_run mode, imported hist data will be saved here
        self.importedDataSource={}
        
        # In the test_run mode, need to know how to simulate real time prices
        # It will be changed in TEST_MarketManager when loading hist data.
        # simulation startTime and endTime is passed from MarketManager to here
        self.modeOfSimulation='random'
        self.startTimeSimulation=None
        self.endTimeSimulation=None
        
        # simulted IB server time, 
        # in the test_run, it will be returned as results of get_datetime()
        self.simulatedServerTime = None 
        
        # a list of orderId has not been filled
        # for test_run mode only
        self.orderIdListToBeFilled=set()        
        
        # Prepare log
        self.todayDateStr = time.strftime("%Y-%m-%d")
        self.log = simpleLogger.SimpleLoggerClass(filename = 
        'TraderLog_' + self.todayDateStr + '.txt', logLevel = self.logLevel)  
        
        # userLog is for the funciton of record (). User will use it for any reason.
        self.dateTimeStr = time.strftime("%Y_%m_%d_%H_%M_%S")
        self.userLog = simpleLogger.SimpleLoggerClass(filename = 
        'userLog_' + self.dateTimeStr + '.txt', logLevel = 'NOTSET', addTime=False)    

        self.log.notset(__name__+'::setup_trader')   
        
    def initialize_Function(self):
        self.log.notset(__name__+'::initialize_Function')
        self.log.info('IBridgePy version %s' %(str(self.versionNumber),))
        self.qData=QDataClass(self)
        self.request_data(ReqData.reqPositions(),
                          ReqData.reqCurrentTime(),
                          ReqData.reqIds())
        self.request_data(ReqData.reqAccountUpdates(True, self.accountCode),
                          ReqData.reqAllOpenOrders())

        self.initialize_quantopian(self.context) # function name was passed in.

        self.log.info('####    Starting to initialize trader    ####')  
        if type(self.accountCode)==type(''):            
            self.display_all()
        else:
            for acctCode in self.accountCode:
                self.display_all(acctCode)
        self.log.info('####    Initialize trader COMPLETED    ####') 
        if self.before_trading_start_quantopian!=None:
            self.schedule_function(func=self.before_trading_start_quantopian, 
                                   time_rule=time_rules.market_open(minutes=-10),
                                   calendar=calendars.US_EQUITIES) 
        tmp = self.get_datetime()
        self.check_date_rules(tmp)
        self.stime_previous = tmp 
        
    def event_Function(self):
        self.log.notset(__name__+'::event_Function')
        if self.realtimeBarCount==0:
            self.handle_data_quantopian(self.context,self.qData) 
            self.realtimeBarCount+=1
        if int(self.repBarFreq/5)+1==self.realtimeBarCount:
            self.realtimeBarCount=0
 
    def repeat_Function(self):
        self.log.notset(__name__+'::repeat_Function: repBarFreq='+str(self.repBarFreq))
        timeNow = self.get_datetime()
        if self.repBarFreq==1 :
            if timeNow.second != self.stime_previous.second:
                self.handle_data_quantopian(self.context,self.qData)
        elif self.repBarFreq==60: # 1 minute, like quantopian style
            if timeNow.minute != self.stime_previous.minute:
                self.handle_data_quantopian(self.context,self.qData)                     
        elif self.repBarFreq in set([2,3,4,5,6,10,15,20,30]):
            if timeNow.second%self.repBarFreq==0 and self.stime_previous.second%self.repBarFreq!=0:
                self.handle_data_quantopian(self.context,self.qData)
        elif self.repBarFreq in set([120,180,300,900,1800]): #1 min,2min,3min,5min,15min,30min
            for ct in range(0,60, int(self.repBarFreq/60)):
                if timeNow.minute==ct and self.stime_previous.minute!=ct:
                    self.handle_data_quantopian(self.context,self.qData)
        elif self.repBarFreq==3600: #hourly
            if timeNow.hour!=self.stime_previous.hour:
                self.handle_data_quantopian(self.context,self.qData)
        else:
            self.log.error(__name__+'::repeat_Function: cannot handle repBarFreq=%i' %(self.repBarFreq,))
            self.end()

        if timeNow.minute != self.stime_previous.minute:
            if self.runToday:
                self.check_schedules()

        self.stime_previous = timeNow
        
    ### supportive functions
    def check_schedules(self):        
        tmp=self.get_datetime(timezone=self.sysTimeZone)
        for ct in self.scheduledFunctionList:
            if self._match(ct.onHour, tmp.hour, 'hourMinute') and\
            self._match(ct.onMinute, tmp.minute, 'hourMinute') and\
            self._match(ct.onNthMonthDay, self.monthDay, 'monthWeek') and\
            self._match(ct.onNthWeekDay, self.weekDay, 'monthWeek'):
                ct.func(self.context, self.qData)
        
    def _match(self,target, val, version):
        if val=='marketClose':
            self.log.error(__name__+'::_match: EXIT val=marketClose')
            self.end()
        if target=='any':
            return True
        else:
            if version=='monthWeek':
                if target>=0:
                    return target==val[0]
                else:
                    return target==val[1]
            elif version=='hourMinute':
                return target==val
            else:
                self.log.error(__name__+'::_match: EXIT, cannot handle version=%s'%(version,))
                self.end()
                
    def check_date_rules(self, aDay):
        '''
        Input:
        aDay: either dt.datetime or dt.date are acceptable
        
        Algo:
        if schedule_funtion is [], then run everyday
        else, strictly follow schedule_function defines !!! IMPORTANT
        
        Output:
        set self.runToday to True(run repeat_func today) or False 
        '''
        self.log.debug(__name__+'::check_date_rules: aDay=%s' %(str(aDay),))
        if type(aDay) == dt.datetime:
            aDay = aDay.date()
        self.monthDay=nth_trading_day_of_month(aDay)
        self.weekDay=nth_trading_day_of_week(aDay)
        if self.monthDay=='marketClose' and self.weekDay=='marketClose':
            self.runToday=False
        elif self.monthDay=='marketClose' and self.weekDay!='marketClose':
            self.log.error(__name__+'::check_date_rules: EXIT,\
            onWeek != marketClose %s'%(str(self.weekDay),))
            exit()
        elif self.monthDay!='marketClose' and self.weekDay=='marketClose':
            self.log.error(__name__+'::check_date_rules: EXIT,\
            onMonth != marketClose %s'%(str(self.monthDay),))
            exit()
        else:
            if self.scheduledFunctionList==[]:
                self.runToday=True
                return
            for ct in self.scheduledFunctionList:
                #print (ct.onNthMonthDay, ct.onNthWeekDay)
                if self._match(ct.onNthMonthDay, self.monthDay, 'monthWeek')\
                         and self._match(ct.onNthWeekDay, self.weekDay, 'monthWeek'):
                    self.runToday=True
                    #print ('TURN ON toay')
                    return
            self.log.debug(__name__+'::check_date_rules: %s = not trading date' %(str(aDay),))
            self.runToday=False
