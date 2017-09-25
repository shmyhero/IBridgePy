# -*- coding: utf-8 -*-
"""
Module MarketManager

"""
import time, pytz
import datetime as dt
from BasicPyLib import small_tools
from BasicPyLib.handle_calendar import nth_trading_day_of_month,nth_trading_day_of_week
from IBridgePy.quantopian import MachineStateClass
from sys import exit

                 
class MarketManager(object):
    """ 
    Market Manager will run trading strategies according to the market hours.
    It should contain a instance of IB's client, properly initialize the connection
    to IB when market starts, and properly close the connection when market closes
    inherited from __USEasternMarketObject__. 
    USeasternTimeZone and run_according_to_market() are inherited
    init_obj(), run_algorithm() and destroy_obj() should be overwritten
    """    
    def __init__(self, trader, host='', port=7496, clientId=99):
        self.host=host
        self.port=port
        self.clientId=clientId
        self.aTrader=trader
        self.marketState = MachineStateClass()
        self.marketState.set_state(self.marketState.SLEEP)
        self.aTrader.log.notset(__name__+'::__init__')
        
        self.lastCheckConnectivityTime=dt.datetime.now()
        self.numberOfConnection=0
        
        # decide if check connectivity every 30 seconds
        self.checkConnectivityFlag=False
        
        # when disconnect between IBridgePY and IB Gateway/TWS, 
        # decide if auto re-connect, try 3 times
        self.autoConnectionFlag=False 
           
    ######### this part do real trading with IB
    def init_obj(self):
        """
        initialzation of the connection to IB
        updated account
        """   
        self.aTrader.log.notset(__name__+'::init_obj')
        self.aTrader.disconnect()
        self.numberOfConnection+=1
        if self.aTrader.connect(self.host, self.port, self.clientId): # connect to server
            self.aTrader.log.debug(__name__ + ": " + "Connected to IB, port = " + 
            str(self.port) + ", ClientID = " + str(self.clientId))
            self.numberOfConnection=0 # reset counter after a successful connection
        else:
            self.aTrader.log.error(__name__+'::init_obj: Not connected')
        time.sleep(1)
                    
    def destroy_obj(self):
        """
        disconnect from IB and close log file
        """
        self.aTrader.log.info('IBridgePy: Disconnect')
        self.aTrader.disconnect()
         
    def run_according_to_market(self, start='9:30', end='16:00'):
        """
        run_according_to_market() will check if market is open every one second
        if market opens, it will first initialize the object and then run the object
        if market closes, it will turn the marketState back to "sleep"
        """

        # print (OPEN/CLOSED immediately after run this function)
        time_now=pytz.timezone(small_tools.localTzname()).localize(dt.datetime.now())
        self.aTrader.log.info(__name__+'::run_accounding_to_market: Start to run_according_to_market')
        if small_tools.if_market_is_open(time_now, start=start, end=end)==False:
            self.aTrader.log.error(__name__+'::run_accounding_to_market: Market is CLOSED now')
        else:
            self.aTrader.log.error(__name__+'::run_accounding_to_market: Market is OPEN now')
  
        while(True):
            # if the market is open, run aTrader
            # if the market is close, disconnect from IB server, and sleep
            time_now=pytz.timezone(small_tools.localTzname()).localize(dt.datetime.now())
            if small_tools.if_market_is_open(time_now, start=start, end=end):            
                if self.marketState.is_state(self.marketState.SLEEP):
                # if the market just open, initialize the trader
                    #self.aTrader.setup_trader()
                    self.init_obj()
                    self.aTrader.initialize_Function()
                    self.marketState.set_state(self.marketState.RUN)
                else:
                # process messages from server every 0.1 second
                    self.aTrader.processMessages()
                    self.aTrader.repeat_Function()
                    time.sleep(0.1)
            else:
            # if the market is closed, disconnect from IB server and sleep.
            # during sleep, check if the market is open on every second
                if self.marketState.is_state(self.marketState.SLEEP):               
                    time.sleep(1)   
                elif self.marketState.is_state(self.marketState.RUN):
                    self.marketState.set_state(self.marketState.SLEEP)                             
                    self.destroy_obj()                    
            
    def run(self):
        self.aTrader.log.debug(__name__+'::run')
        self.init_obj()
        if self.aTrader.isConnected():
            self.aTrader.connectionGatewayToServer=True
            self.aTrader.initialize_Function()
            while(not self.aTrader.wantToEnd):
                self.aTrader.processMessages()
                if self.checkConnectivityFlag:
                    if self.check_connectivity():
                        if self.aTrader.connectionGatewayToServer:
                            self.aTrader.repeat_Function()
                            time.sleep(0.1)
                        else:
                            time.sleep(1)
                    else:
                        self.aTrader.wantToEnd=False
                        break 
                else:
                    self.aTrader.repeat_Function()
                    time.sleep(0.1)                  
        if not self.autoConnectionFlag:
            self.destroy_obj()

        

    def run_like_quantopian(self):
        self.aTrader.log.debug(__name__+'::run_like_quantopian: START')
        self.init_obj()
        if self.aTrader.isConnected():
            self.aTrader.connectionGatewayToServer=True
            self.aTrader.initialize_Function() 
            while (not self.aTrader.wantToEnd):
                # a new day start, calculate if today is a schedued day
                #if yes run handle_date
                #if not, run processMessage() only
                #print (self.aTrader.get_datetime(), self.aTrader.stime_previous )
                timeNow = self.aTrader.get_datetime()
                if timeNow.day != self.aTrader.stime_previous.day:
                    self.check_date_rules(timeNow.date())
                if self.aTrader.runToday:          
                    self.aTrader.processMessages()
                    if self.checkConnectivityFlag:
                        if self.check_connectivity():
                            if self.aTrader.connectionGatewayToServer:
                                self.aTrader.repeat_Function()
                                time.sleep(0.1)
                            else:
                                time.sleep(1)
                        else:
                            self.aTrader.wantToEnd=False
                            break 
                    else:
                        self.aTrader.repeat_Function()
                        time.sleep(0.1)                       
                else:
                    self.aTrader.processMessages()
                    self.aTrader.stime_previous=timeNow
                    time.sleep(1)
        if not self.autoConnectionFlag:
            self.destroy_obj()

    def runOnEvent(self):
        self.aTrader.log.debug(__name__+'::runOnEvent')
        self.init_obj()
        if self.aTrader.repBarFreq%5!=0:
            self.aTrader.log.error(__name__+'::runOnEvent: EXIT, cannot handle reqBarFreq=%s' %(str(self.aTrader.repBarFreq),))
            exit()
        self.aTrader.initialize_Function()
        while self.aTrader.realtimeBarTime==None:
            time.sleep(0.2)
            self.aTrader.processMessages()
            self.aTrader.log.notset(__name__+'::runOnEvent: waiting realtimeBarTime is called back')
            
        while self.aTrader.realtimeBarTime.second!=55:
        # when the realtimeBarTime.second==55 comes in, the IB server time.second==0
        # start the handle_data when second ==0
        # Set realtimeBarCount=0
        # realtimeBarCount+=1 when a new bar comes in
            time.sleep(0.2)
            self.aTrader.processMessages()
        self.aTrader.realtimeBarCount=0
        self.aTrader.event_Function()
        
        while(True):
            self.aTrader.processMessages()
            self.aTrader.event_Function()
            time.sleep(1)
 
    def run_auto_connection(self, tryTimes=3):
        self.aTrader.wantToEnd=False
        self.autoConnectionFlag=True
        self.checkConnectivityFlag=True
        while self.numberOfConnection<=tryTimes:
            self.run()
            if self.aTrader.wantToEnd:
                break
            else:
                self.aTrader.log.error(__name__+'::run_auto_connection:wait 30\
                seconds to reconnect')
                self.aTrader.connectionGatewayToServer=False
                time.sleep(30)
                if self.numberOfConnection>tryTimes:
                    break
        if not self.aTrader.wantToEnd:
            print (__name__+'::run_auto_connection: END. tried 3 times\
            but cannot conect to Gateway.' ) 
        else:
            print (__name__+'::run_auto_connection: END')             

    def check_date_rules(self, aDay):
        self.aTrader.monthDay=nth_trading_day_of_month(aDay)
        self.aTrader.weekDay=nth_trading_day_of_week(aDay)
        #print (tmp, self.aTrader.monthDay, self.aTrader.weekDay)
        if self.aTrader.monthDay=='marketClose' and self.aTrader.weekDay=='marketClose':
            self.aTrader.runToday=False
        elif self.aTrader.monthDay=='marketClose' and self.aTrader.weekDay!='marketClose':
            self.aTrader.log.error(__name__+'::run_like_quantopian: EXIT,\
            onWeek != marketClose %s'%(str(self.aTrader.weekDay),))
            exit()
        elif self.aTrader.monthDay!='marketClose' and self.aTrader.weekDay=='marketClose':
            self.aTrader.log.error(__name__+'::run_like_quantopian: EXIT,\
            onMonth != marketClose %s'%(str(self.aTrader.monthDay),))
            exit()
        else:
            if self.aTrader.scheduledFunctionList==[]:
                self.aTrader.runToday=True
                return
            for ct in self.aTrader.scheduledFunctionList:
                #print (ct.onNthMonthDay, ct.onNthWeekDay)
                if self.aTrader._match(ct.onNthMonthDay, self.aTrader.monthDay, 'monthWeek')\
                         and self.aTrader._match(ct.onNthWeekDay, self.aTrader.weekDay, 'monthWeek'):
                    self.aTrader.runToday=True
                    #print ('TURN ON toay')
                    return
            #print ('OFF today')
            self.aTrader.runToday=False

    def check_connectivity(self):
        if self.aTrader.connectionGatewayToServer==False:
            return True
            
        setTimer=dt.datetime.now()
        #print (setTimer-self.lastCheckConnectivityTime).total_seconds()
        if (setTimer-self.lastCheckConnectivityTime).total_seconds()<30:
            return True
        self.aTrader.log.debug(__name__+'::check_connectivity')
        self.aTrader.nextId=None
        self.aTrader.reqIds(0)
        checkTimer=dt.datetime.now()
        while (checkTimer-setTimer).total_seconds()<0.5:
            self.aTrader.processMessages()
            if self.aTrader.nextId!=None:
                self.lastCheckConnectivityTime=checkTimer
                self.aTrader.log.debug(__name__+'::check_connectivity:GOOD')
                return True
            self.aTrader.log.debug(__name__+'::check_connectivity:checking ...')
            time.sleep(0.05)
            checkTimer=dt.datetime.now()
        self.aTrader.log.debug(__name__+'::check_connectivity:BAD')
        return False
            
if __name__=='__main__':                            
    c=test()
    d=MarketManager(c)
    d.init_obj()
          