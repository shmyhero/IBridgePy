# -*- coding: utf-8 -*-
"""
Module MarketManager

"""
import datetime as dt
from IBridgePy.quantopian import MachineStateClass
from sys import exit
import time
                 
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
                timeNow = self.aTrader.get_datetime()
                #print (__name__, timeNow, self.aTrader.stime_previous)
                if timeNow.day != self.aTrader.stime_previous.day:
                    self.aTrader.check_date_rules(timeNow.date())
        
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
          