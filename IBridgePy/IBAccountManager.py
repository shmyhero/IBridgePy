# -*- coding: utf-8 -*-
'''
There is a risk of loss in stocks, futures, forex and options trading. Please
trade with capital you can afford to lose. Past performance is not necessarily 
indicative of future results. Nothing in this computer program/code is intended
to be a recommendation to buy or sell any stocks or futures or options or any 
tradable securities. 
All information and computer programs provided is for education and 
entertainment purpose only; accuracy and thoroughness cannot be guaranteed. 
Readers/users are solely responsible for how they use the information and for 
their results.

If you have any questions, please send email to IBridgePy@gmail.com
'''
import time
import pandas as pd
import numpy as np
import pytz

from IBridgePy.quantopian import Security, PositionClass, \
create_contract, MarketOrder, OrderClass, same_security, \
DataClass,from_contract_to_security,EndCheckListClass, \
ReqHistClass, from_symbol_to_security, calendars, \
TimeBasedRules,search_security_in_Qdata

from IBridgePy import IBCpp
import datetime as dt 
from sys import exit
from copy import deepcopy

# https://www.interactivebrokers.com/en/software/api/apiguide/tables/tick_types.htm
MSG_TABLE = {0: 'bid size', 1: 'bid price', 2: 'ask price', 3: 'ask size', 
             4: 'last price', 5: 'last size', 6: 'daily high', 7: 'daily low', 
             8: 'daily volume', 9: 'close', 14: 'open'}
priceNameChange={'price':'last_traded','open':'open', 'high':'high', 'low':'low',
                 'close':'close', 'ask_price':'ask_price', 
                 'bid_price':'bid_price', 'ask_size':'ask_size',
                 'bid_size':'bid_size', 'last_price':'last_traded'}

class IBAccountManager(IBCpp.IBClient):
    """
    IBAccountManager manages the account, order, and historical data information
    from IB. These information are needed by all kinds of traders.
    """         
                       
    def error(self, errorId, errorCode, errorString):
        """
        only print real error messages, which is errorId < 2000 in IB's error
        message system, or program is in debug mode
        """
        if errorCode in [2119,2104,2108,2106, 2107, 2103]:
            pass
        else:
            self.log.error(__name__ + ": " + 'errorId = ' + str(errorId) + 
            ', errorCode = ' + str(errorCode) + ', error message: ' + errorString)
            if errorCode==1100:
                self.connectionGatewayToServer=False
            elif errorCode in [1101, 1102]:
                self.connectionGatewayToServer=True
            elif errorCode==1300:
                exit()
                
            elif errorCode==320:
                exit()

            elif errorCode == 504:
                self.log.error(__name__ + ": " + 'errorId = ' + str(errorId) + 
                ', errorCode = ' + str(errorCode) + ', error message: ' + errorString)
            
    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the showTimeZone from MarketManager
        """
        self.log.notset(__name__+'::currentTime')
        self.recordedServerUTCtime=tm # float, utc number
        self.recordedLocalTime = dt.datetime.now() # a datetime, without tzinfo
                                                 
    def roundToMinTick(self, price, minTick=0.01):
        """
        for US interactive Brokers, the minimum price change in US stocks is
        $0.01. So if the user made calculations on any price, the calculated
        price must be round using this function to the minTick, e.g., $0.01
        """
        if price<0.0:
            self.log.error(__name__ + '::roundToMinTick price: EXIT, negtive price ='+str(price))
            self.end()            
        rounded=int(price / minTick) * minTick
        self.log.debug(__name__ + '::roundToMinTick price: round ' + str(price) +'to ' + str(rounded))
        return rounded

    def set_timer(self):
        """
        set self.timer_start to current time so as to start the timer
        """
        self.timer_start = dt.datetime.now()
        self.log.notset(__name__ + "::set_timer: " + str(self.timer_start))
        
    def check_timer(self, limit = 1):
        """
        check_timer will check if time limit exceeded for certain
        steps, including: updated positions, get nextValidId, etc
        """
        self.log.notset(__name__+'::check_timer:')
        timer_now = dt.datetime.now()
        change = (timer_now-self.timer_start).total_seconds()
        if change > limit: # if time limit exceeded
            self.log.error(__name__+ '::check_timer: request_data failed after '+str(limit)+' seconds')
            self.log.error(__name__+'::check_timer: notDone items in self.end_check_list')           
            tp=self.search_in_end_check_list(notDone=True, output_version='list')
            for ct in tp:
                self.log.error(str(tp[ct]))            
            return True
        else:
            return None
  
    def nextValidId(self, orderId):
        """
        IB API requires an orderId for every order, and this function obtains
        the next valid orderId. This function is called at the initialization 
        stage of the program and results are recorded in startingNextValidIdNumber,
        then the orderId is track by the program when placing orders
        """        
        self.log.debug(__name__ + '::nextValidId: Id = ' + str(orderId))
        self.nextId = orderId
                                                 
    def update_DataClass(self, security, name, value=None, ls_info=None):
        self.log.notset(__name__+'::update_DataClass')  
        if ls_info==None and value!=None:
            if (self.maxSaveTime > 0 and value > 0):
                currentTimeStamp = time.mktime(dt.datetime.now().timetuple())
                newRow = [currentTimeStamp, value]
                tmp = getattr(self.qData.data[security], name)
                tmp = np.vstack([tmp, newRow])
                # erase data points that go over the limit
                if (currentTimeStamp - tmp[0, 0]) > self.maxSaveTime:
                    tmp = tmp[1:,:]
                setattr(self.qData.data[security], name, tmp)
        elif ls_info!=None and value==None:
            if name=='realTimeBars':
                if len(ls_info)!=8:
                    self.log.error(__name__+'::update_DataClass: ls_info does not matach data structure of '+name)
                    self.end()
            currentTimeStamp = time.mktime(dt.datetime.now().timetuple())
            newRow = [currentTimeStamp]+ls_info
            tmp = getattr(self.qData.data[security], name)
            tmp = np.vstack([tmp, newRow])
            # erase data points that go over the limit
            if (currentTimeStamp - tmp[0, 0]) > self.maxSaveTime:
                tmp = tmp[1:,:]
            setattr(self.qData.data[security], name, tmp)
            
        
    def tickPrice(self, reqId, tickType, price, canAutoExecute):
        """
        call back function of IB C++ API. This function will get tick prices
        """
        self.log.notset(__name__+'::tickPrice:'+str(reqId)+' '+str(tickType)+' '+str(price))

        # security found is garuanteed to be in self.qData.data
        # no need to search it anymore.
        security=self._reqId_to_security(reqId)
   
        self.qData.data[security].datetime=self.get_datetime()
        if tickType==1: #Bid price
            self.qData.data[security].bid_price = price
            self.update_DataClass(security, 'bid_price_flow', price)
            if security.secType=='CASH':
                self.qData.data[security].last_traded = price   
        elif tickType==2: #Ask price
            self.qData.data[security].ask_price = price
            self.update_DataClass(security, 'ask_price_flow', price)
        elif tickType==4: #Last price
            self.qData.data[security].last_traded = price
            self.update_DataClass(security, 'last_traded_flow', price)
        elif tickType==6: #High daily price
            self.qData.data[security].high=price
        elif tickType==7: #Low daily price
            self.qData.data[security].low=price
        elif tickType==9: #last close price
            self.qData.data[security].close = price
        elif tickType == 14:#open_tick
            self.qData.data[security].open = price
        else:
            self.log.error(__name__+'::tickPrice: unexpected tickType=%i' %(tickType,))


    def tickSize(self, reqId, tickType, size):
        """
        call back function of IB C++ API. This function will get tick size
        """
        self.log.notset(__name__+'::tickSize: ' + str(reqId) + ", " + MSG_TABLE[tickType]
        + ", size = " + str(size))
        security=self._reqId_to_security(reqId) #same thing in tickPrice
        if security == None:
            return 0
        self.qData.data[security].datetime=self.get_datetime()
        if tickType == 0: # Bid Size
            self.qData.data[security].bid_size = size
            #self.update_DataClass(security, 'bid_size_flow', size)
        if tickType == 3: # Ask Size
            self.qData.data[security].ask_size = size
            #self.update_DataClass(security, 'ask_size_flow', size)  
        if tickType == 3: # Last Size
            self.qData.data[security].size = size
            #self.update_DataClass(security, 'last_size_flow', size)
        if tickType == 8: # Volume
            self.qData.data[security].volume = size
                    
    def tickString(self, reqId, field, value):
        """
        IB C++ API call back function. The value variable contains the last 
        trade price and volume information. User show define in this function
        how the last trade price and volume should be saved
        RT_volume: 0 = trade timestamp; 1 = price_last, 
        2 = size_last; 3 = record_timestamp
        """
        self.log.debug(__name__+'::tickString: ' + str(reqId)
         + 'field=' +str(field) + 'value='+str(value))
        #print (reqId, field)

        security=self._reqId_to_security(reqId) #same thing in tickPrice
        if security == None:
            #self.log.debug('cannot find it')
            return 0
       
        if str(field)=='RT_VOLUME':
            currentTime = self.get_datetime()
            valueSplit = value.split(';')
            if valueSplit[0]!='':
                priceLast = float(valueSplit[0])
                timePy = float(valueSplit[2])/1000
                sizeLast = float(valueSplit[1])
                currentTimeStamp = time.mktime(dt.datetime.now().timetuple())
                self.log.notset(__name__ + ':tickString, ' + str(reqId) + ", " 
                + str(security.symbol) + ', ' + str(priceLast)
                + ", " + str(sizeLast) + ', ' + str(timePy) + ', ' + str(currentTime))
                # update price
                newRow = [timePy, priceLast, sizeLast, currentTimeStamp]
                #newRow = [timePy, priceLast, sizeLast]
                priceSizeLastSymbol = self.qData.data[security].RT_volume
                priceSizeLastSymbol = np.vstack([priceSizeLastSymbol, newRow])
                # erase data points that go over the limit
                if (timePy - priceSizeLastSymbol[0, 0]) > self.maxSaveTime:
                    #print (timePy, priceSizeLastSymbol[0, 0])
                    #print ('remove')
                    priceSizeLastSymbol = priceSizeLastSymbol[1:,:]
                self.qData.data[security].RT_volume = priceSizeLastSymbol
                #print (self.qData.data[security].RT_volume)
            #except:
            #    self.log.info(__name__+'::tickString: ' + str(reqId)
            #     + 'field=' +str(field) + 'value='+str(value))
                 # priceLast = float(valueSplit[0])
                 #ValueError: could not convert string to float:
            #    self.end()
                
    def historicalData(self, reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps):
        """
        call back function from IB C++ API
        return the historical data for requested security
        """
        self.log.notset(__name__+'::historicalData: reqId='+str(reqId)+','+date)
        loc=self.search_in_end_check_list(reqId=reqId, reqType='historyData')
        
        if self.receivedHistFlag==False:
            sec=self.end_check_list[loc].security
            barSize=self.end_check_list[loc].input_parameters.barSize
            self.log.debug(__name__+'::historicalData: Received 1st row %s %s'%(sec,barSize))
            self.receivedHistFlag=True
             
        if 'finished' in str(date):
            self.end_check_list[loc].status='Done'       
            
            #if the returned security is in self.qData.data, put the historicalData into self.qData.data
            # else, add the new security in self.qData.data
            sec=self.end_check_list[loc].security
            barSize=self.end_check_list[loc].input_parameters.barSize
            self.qData.data[search_security_in_Qdata(self.qData,sec, self.logLevel)].hist[barSize]=self.end_check_list[loc].return_result               
            self.log.notset(__name__ + '::historicalData: finished req hist data for '+str(sec))
            self.log.notset('First line is ')
            self.log.notset(str(self.end_check_list[loc].return_result.iloc[0]))
            self.log.notset('Last line is ')
            self.log.notset(str(self.end_check_list[loc].return_result.iloc[-1]))
            
        else:
            if self.end_check_list[loc].input_parameters.formatDate==1:
                if '  ' in date:                       
                    date=dt.datetime.strptime(date, '%Y%m%d  %H:%M:%S') # change string to datetime                        
                else:
                    date=dt.datetime.strptime(date, '%Y%m%d') # change string to datetime
            else: # formatDate is UTC time in seconds, str type 
                if len(date)>9: # return datetime, not date
                    date = dt.datetime.fromtimestamp(float(date), tz = pytz.utc)
                    date = date.astimezone(self.showTimeZone)
                    #date = dt.datetime.strftime(date, '%Y-%m-%d  %H:%M:%S %Z')                                      
                else: # return date, not datetime
                    date=dt.datetime.strptime(date, '%Y%m%d') # change string to datetime
                    #date=pytz.utc.localize(date)
                    #date = date.astimezone(self.showTimeZone)
                    #date = dt.datetime.strftime(date, '%Y-%m-%d %Z')                                      

            if date in self.end_check_list[loc].return_result.index:
                self.end_check_list[loc].return_result['open'][date]=price_open
                self.end_check_list[loc].return_result['high'][date]=price_high
                self.end_check_list[loc].return_result['low'][date]=price_low
                self.end_check_list[loc].return_result['close'][date]=price_close
                self.end_check_list[loc].return_result['volume'][date]=volume
            else:
                newRow = pd.DataFrame({'open':price_open,'high':price_high,
                                       'low':price_low,'close':price_close,
                                       'volume':volume}, index = [date])
                self.end_check_list[loc].return_result=self.end_check_list[loc].return_result.append(newRow)

    def realtimeBar(self, reqId, time, price_open, price_high, price_low, price_close, volume, wap, count):
        """
        call back function from IB C++ API
        return realTimebars for requested security every 5 seconds
        """
        self.log.debug(__name__+'::realtimeBar: reqId='+str(reqId)+','+str(dt.datetime.fromtimestamp(time)))
        security=self._reqId_to_security(reqId) #same thing in tickPrice             
        self.update_DataClass(security, 'realTimeBars', ls_info=[time, price_open, price_high, price_low, price_close, volume, wap, count])
        self.realtimeBarCount+=1 
        self.realtimeBarTime=dt.datetime.fromtimestamp(time)   
                            
    def updateAccountTime(self, tm):
        self.log.notset(__name__+'::updateAccountTime:'+str(tm))
        
    def accountSummaryEnd(self, reqId):
        self.log.error(__name__ + '::accountSummaryEnd:CANNOT handle' + str(reqId))
        self.end()

    def execDetails(self, reqId, contract, execution):
        self.log.notset(__name__+'::execDetails: DO NOTHING reqId'+str(reqId))     

    def commissionReport(self,commissionReport):
        self.log.notset(__name__+'::commissionReport: DO NOTHING'+str(commissionReport))        

        
    def positionEnd(self):
        self.log.notset(__name__+'::positionEnd: all positions recorded')
        ct=self.search_in_end_check_list(reqType='positions')
        self.end_check_list[ct].status='Done'
           
    def tickSnapshotEnd(self, reqId):
        self.log.notset(__name__+'::tickSnapshotEnd: '+str(reqId))
        ct=self.search_in_end_check_list(reqType='marketSnapShot', reqId=reqId)
        self.end_check_list[ct].status='Done'
                                 
    def get_datetime(self, timezone='default'):
        """
        function to get the current datetime of IB system similar to that
        defined in Quantopian
        """
        self.log.notset(__name__+'::get_datetime_quantopian')
        if self.runMode==None:
            tmp=(dt.datetime.now()-self.recordedLocalTime).total_seconds()
            tmp+=self.recordedServerUTCtime
            ans=dt.datetime.fromtimestamp(tmp, tz=pytz.utc)
            if timezone=='default':
                return ans.astimezone(self.showTimeZone)
            else:
                return ans.astimezone(timezone)
        else:
            return self.simulatedServerTime.astimezone(self.showTimeZone)

    def contractDetails(self, reqId, contractDetails):
        '''
        IB callback function to receive contract info
        '''
        self.log.notset(__name__+'::contractDetails:'+str(reqId))                                     
        ct=self.search_in_end_check_list(reqId=reqId, reqType='contractDetails')
        if contractDetails.summary.secType=='STK':
            newRow=pd.DataFrame({'contract':self._print_contract(contractDetails.summary),
                                 'marketName':contractDetails.marketName,
                                 'validExchange':contractDetails.validExchanges,
                                 'minTick':contractDetails.minTick,
                                 'longName':contractDetails.longName,
                                 'contractDetails':contractDetails
                                 },index=[0])
        else:
            newRow=pd.DataFrame({'right':contractDetails.summary.right,
                                 'strike':float(contractDetails.summary.strike),
                                 'expiry':dt.datetime.strptime(contractDetails.summary.expiry, '%Y%m%d'),
                                 'contract':self._print_contract(contractDetails.summary),
                                 'multiplier':contractDetails.summary.multiplier,
                                 'contractDetails':contractDetails
                                 },index=[0])
        self.end_check_list[ct].return_result=self.end_check_list[ct].return_result.append(newRow)

    def contractDetailsEnd(self, reqId):
        '''
        IB callback function to receive the ending flag of contract info
        '''
        self.log.debug(__name__+'::contractDetailsEnd:'+str(reqId))
        ct=self.search_in_end_check_list(reqId=reqId)
        self.end_check_list[ct].status='Done'
        self.qData.data[search_security_in_Qdata(self.qData,self.end_check_list[ct].security, self.logLevel)].contractDetails=self.end_check_list[ct].return_result

    def tickGeneric(self, reqId, field, value):
        self.log.notset(__name__+'::tickGeneric: reqId=%i field=%s value=%d'\
        %(reqId, field, value))
        #exit()
        
    def tickOptionComputation(self, reqId, tickType, impliedVol, delta,
                              optPrice, pvDividend, gamma, vega, theta, 
                              undPrice):
        self.log.debug(__name__+'::tickOptionComputation:'+str(reqId))
        self.log.debug(__name__+'::tickOptionComputation:\
        %s %s %s %s %s %s %s %s %s' %(\
        tickType, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta, 
                              undPrice) )
        # security found is garuanteed to be in self.qData.data
        # no need to search it anymore.
        security=self._reqId_to_security(reqId)
        self.qData.data[security].impliedVol=impliedVol
        self.qData.data[security].delta=delta
        self.qData.data[security].gamma=gamma
        self.qData.data[security].vega=vega
        self.qData.data[security].theta=theta
        self.qData.data[security].undPrice=undPrice
        

        
    
    ####### SUPPORTIVE functions ###################
    def end(self):
        self.log.debug(__name__+'::end')          
        self.wantToEnd=True
    
    def _request_real_time_price(self, security, waiver):
        self.log.notset(__name__+'::_request_real_time_price:'+str(security))  
        re=search_security_in_Qdata(self.qData,security, self.logLevel)        
        if waiver:
            self.request_data(realTimePrice=[re],waiver=['realTimePrice'])
        else:
            self.request_data(realTimePrice=[re])

    def _reqId_to_security(self, reqId):    
        self.log.notset(__name__+'::_reqId_to_security'+str(reqId))  
        if reqId in self.realTimePriceRequestedList:
            return self.realTimePriceRequestedList[reqId]
        else:
            self.log.error(__name__+'::_reqId_to_security: EXIT, reqId not in self.realTimePriceRequestedList')
            self.end()

    def _load_hist(self, security, hist_df, frequency):
        adj_security=search_security_in_Qdata(self.qData, security, self.logLevel)        
        self.qData.data[adj_security].hist[frequency]=hist_df

    def _save_info(self, security):  
        self.log.debug(__name__+'::_save_info')
        sec=search_security_in_Qdata(self.qData, security, self.logLevel)               
        # put security and reqID in dictionary for fast acess
        # it is keyed by both security and reqId
        self.realTimePriceRequestedList[sec]=self.nextId
        self.realTimePriceRequestedList[self.nextId]=sec
        return sec
    
    def _print_contract(self, cntrct):
        if cntrct.secType=='OPT':
            return cntrct.secType+','+\
            str(cntrct.symbol)+','+\
            str(cntrct.primaryExchange)+','+\
            str(cntrct.exchange)+','+\
            str(cntrct.currency)+','+\
            str(cntrct.expiry)+','+\
            str(cntrct.strike)+','+\
            str(cntrct.right)+','+\
            str(cntrct.multiplier)   
        elif cntrct.secType=='STK' or cntrct.secType=='CASH' or cntrct.secType=='CFD':
            return cntrct.secType+','+\
            str(cntrct.symbol)+','+\
            str(cntrct.primaryExchange)+','+\
            str(cntrct.exchange)+','+\
            str(cntrct.currency)

        elif cntrct.secType=='FUT':
            return cntrct.secType+','+\
            str(cntrct.symbol)+','+\
            str(cntrct.primaryExchange)+','+\
            str(cntrct.exchange)+','+\
            str(cntrct.currency)+','+\
            str(cntrct.expiry)
        else:
            self.log.error(__name__+'::_print_contract: EXIT, cannot handle secType=%s' %(cntrct.secType,))
            exit()      

    def get_option_greeks(self, securityOption, itemName=None):
        '''
        itemName can be a string 'delta' or a list of string
        '''
        ans={}
        if itemName==None:
            itemList=['delta', 'gamma', 'vega', 'theta', 'impliedVol']
        else:
            if type(itemName)==str:
                itemList=[itemName]
            elif type(itemName)==list:
                itemList=itemName
            else:
                self.log.error(__name__='::get_option_greeks: EXIT, cannot\
                handle itemName=%s' %(itemName,))
                exit()
        for ct in itemList:
            if ct not in ['delta', 'gamma', 'vega', 'theta', 'impliedVol']:
                self.log.error(__name__='::get_option_greeks: EXIT, cannot\
                handle itemName=%s' %(itemName,))
                exit()
            else:                
                ans[ct]=getattr(self.qData.data[securityOption], ct)
        return ans
               
    def request_historical_data(self, security,
                                        barSize,
                                        goBack,
                                        endTime='default',
                                        whatToShow=None,
                                        useRTH=1,
                                        formatDate=2,
                                        waitForFeedbackinSeconds=30):
        if endTime=='default':
            endTime=self.get_datetime()
        tmp=ReqHistClass(security=security,
                    barSize=barSize,
                    goBack=goBack,
                    endTime=endTime,
                    whatToShow=whatToShow,
                    useRTH=useRTH,
                    formatDate=formatDate,
                    showTimeZone=self.showTimeZone)                                    
        self.request_data(historyData=[tmp],
                          waitForFeedbackinSeconds=waitForFeedbackinSeconds)
        adj_security=search_security_in_Qdata(self.qData, security,
                                              self.logLevel)        
        return deepcopy(self.qData.data[adj_security].hist[barSize])                                  
            
    def symbol(self, str_security):
        self.log.notset(__name__+'::symbol:'+str_security)  
        a_security=from_symbol_to_security(str_security, self.logLevel)
        re=search_security_in_Qdata(self.qData, a_security, self.logLevel)  
        self.build_security_in_positions(a_security, accountCode='all')
        return re

    def symbols(self, *args): 
        self.log.notset(__name__+'::symbols:'+str(args))  
        ls=[]
        for item in args:
            ls.append(self.symbol(item))
        return ls 

    def superSymbol(self, secType=None,
                    symbol=None,
                    currency='USD',
                    exchange='',
                    primaryExchange='',
                    expiry='',
                    strike=-1,
                    right='',
                    multiplier=-1,
                    includeExpired=False):
        self.log.notset(__name__+'::superSymbol')  
        a_security= Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange, expiry=expiry,
                    strike=strike, right=right, multiplier=multiplier, includeExpired=includeExpired)  
        re=search_security_in_Qdata(self.qData, a_security, self.logLevel)
        self.build_security_in_positions(a_security, accountCode='all')
        return re
           
    def search_in_end_check_list(self, reqType=None, security=None, \
                        reqId=None, notDone=None, output_version='location', allowToFail=False):
        self.log.notset(__name__+'::search_in_end_check_list')  
        search_result={}
        input_list=self.end_check_list
        if reqType!=None:
            for ct in input_list:
                if input_list[ct].reqType==reqType:
                    search_result[ct]=input_list[ct]
            input_list=search_result
            search_result={}
            
        if security!=None:    
            for ct in input_list:
                if same_security(input_list[ct].security,security):
                    search_result[ct]=input_list[ct]
            input_list=search_result
            search_result={}
                    
        if reqId!=None:                                       
            for ct in input_list:          
                if input_list[ct].reqId==reqId:
                    search_result[ct]=input_list[ct]
            input_list=search_result
            search_result={}
                                        
        if notDone!=None:                                       
            for ct in input_list:          
                if input_list[ct].status!='Done':
                    search_result[ct]=input_list[ct]
            input_list=search_result
            search_result={}

        if output_version=='location':
            if len(input_list)==0:
                if allowToFail==False:
                    self.log.error(__name__+'::search_in_end_check_list: cannot\
                    find any in self.end_check_list %s %s %i %s' %(reqType, str(security), reqId, notDone))
                    self.end()
                else:
                    return None
            elif len(input_list)==1:
                for ct in input_list:
                    return ct
            else:
                self.log.error(__name__+'::search_in_end_check_list: found too many in self.end_check_list, EXIT')
                for ct in input_list:
                    self.log.error(str(input_list[ct]))
                self.end()
        elif output_version=='list':
            return input_list
        else:
            self.log.error(__name__+'::search_in_end_check_list: cannot handle oupt_version='+output_version)
            

    def display_end_check_list(self):
        self.log.info(__name__+'::display_end_check_list')
        if len(self.end_check_list)==0:
            self.log.info(__name__+'::display_end_check_list: EMPTY self.end_check_list')
        else:    
            for ct in self.end_check_list:
                self.log.info(__name__+'::display_end_check_list: '+ str(ct)+' '+str(self.end_check_list[ct]))
            self.log.info(__name__+'::display_end_check_list: END     #############')

        

    def show_nextId(self):
        return self.nextId
        
    def show_real_time_price(self, security, version):
        self.log.notset(__name__+'::show_real_time_price')                          
        adj_security=search_security_in_Qdata(self.qData,security, self.logLevel)
        version=priceNameChange[version]
        if adj_security not in self.realTimePriceRequestedList:
            self.request_data(realTimePrice=[adj_security],waiver=['realTimePrice'])    
        if hasattr(self.qData.data[adj_security], version):
            return getattr(self.qData.data[adj_security], version)
        else:
            self.log.error(__name__+'::show_real_time_price: EXIT, cannot handle version='+version)
            self.end()
            
    def show_latest_price(self, security):
        self.log.notset(__name__+'::show_latest_price')                          
        adj_security=search_security_in_Qdata(self.qData,security, self.logLevel)
        if self.qData.data[adj_security].last_traded<0.01:
            self.request_data(marketSnapShot=[adj_security])
        return self.qData.data[adj_security].last_traded    




    def create_order(self, action, amount, security, orderDetails, 
                     ocaGroup=None, ocaType=None, transmit=None, parentId=None,
                     orderRef=''):
        self.log.debug(__name__+'::create_order:'+str(amount) )                
        contract=create_contract(security)
        order = IBCpp.Order()
        order.action = action      # BUY, SELL
        order.totalQuantity = amount
        order.orderType = orderDetails.orderType  #LMT, MKT, STP
        order.tif=orderDetails.tif 
        order.orderRef=str(orderRef)
        if ocaGroup !=None:
            order.ocaGroup=ocaGroup
        if ocaType!=None:
            order.ocaType=ocaType 
        if transmit != None:
            order.transmit=transmit   
        if parentId != None:
            order.parentId=parentId
            
        if orderDetails.orderType=='MKT':
            pass
        elif orderDetails.orderType=='LMT':    
            order.lmtPrice=orderDetails.limit_price
        elif orderDetails.orderType=='STP':
            order.auxPrice=orderDetails.stop_price
        elif orderDetails.orderType=='STP LMT':
            order.lmtPrice=orderDetails.limit_price
            order.auxPrice=orderDetails.stop_price
        elif orderDetails.orderType=='TRAIL LIMIT':
            order.lmtPrice=orderDetails.stop_price-orderDetails.limit_offset
            order.trailingPercent=orderDetails.trailing_percent  # trailing percentage
            order.trailStopPrice=orderDetails.stop_price
        else:
            self.log.error(__name__+'::create_super_order: EXIT, Cannot handle order type=%s' %(orderDetails.orderType,))
            self.end()  
        return OrderClass(contract=contract, order=order)

    def place_combination_orders(self, legList):
        '''
        legList is a list of created orders that are created by create_order( )
        '''
        finalOrderIdList=[]
        for leg in legList:
            orderId=self.IBridgePyPlaceOrder(leg)
            finalOrderIdList.append(orderId)
        return finalOrderIdList
                                 
    def place_order_with_TP_SL(self, parentOrder, tpOrder, slOrder):
        '''
        return orderId of the parentOrder only
        '''
        tpOrder.order.parentId=self.nextId
        slOrder.order.parentId=self.nextId
        parentOrder.order.transmit=False
        tpOrder.order.transmit=False
        slOrder.order.transmit=True
        orderId=self.IBridgePyPlaceOrder(parentOrder)
        self.IBridgePyPlaceOrder(tpOrder)
        self.IBridgePyPlaceOrder(slOrder)
        return orderId

    def cancel_order(self, order):
        """
        function to cancel orders
        """
        self.log.notset(__name__+'::cancel_order')  

        if isinstance(order, OrderClass):
            self.cancelOrder(order.orderId)
        else:
            self.cancelOrder(int(order))
            
    #### Match Quantopian functions      
    
    def schedule_function(self,
                          func, 
                          date_rule=None,
                          time_rule=None,
                          calendar=calendars.US_EQUITIES):
        if time_rule==None:
            onHour='any' # every number can match, run every hour
            onMinute='any'  # every number can match, run every minute
        else:
            # if there is a time_rule, calculate onHour and onMinute based on markettimes
            marketOpenHour,marketOpenMinute,marketCloseHour,marketCloseMinute=calendar
            #print (marketpenHour,marketOpenMinute,marketCloseHour,marketCloseMinute)
            marketOpen=marketOpenHour*60+marketOpenMinute
            marketClose=marketCloseHour*60+marketCloseMinute
            if time_rule.version=='market_open' or time_rule.version=='market_close':
                if time_rule.version=='market_open':
                    tmp=marketOpen+time_rule.hour*60+time_rule.minute
                else:
                    tmp=marketClose-time_rule.hour*60-time_rule.minute
                while tmp<0:
                    tmp+=24*60
                startTime=tmp%(24*60)
                onHour=int(startTime/60)
                onMinute=int(startTime%60)  
            elif time_rule.version=='spot_time':
                onHour=time_rule.hour
                onMinute=time_rule.minute
            else:
                self.log.error (__name__+'::schedule_function: EXIT, cannot handle time_rule.version=%s'%(time_rule.version,))
                self.end()

        if date_rule==None:
            # the default rule is None, means run every_day
            tmp=TimeBasedRules(onHour=onHour,onMinute=onMinute,func=func)
            self.scheduledFunctionList.append(tmp) 
            return
        else:
            if date_rule.version=='every_day':
                tmp=TimeBasedRules(onHour=onHour,onMinute=onMinute,func=func)
                self.scheduledFunctionList.append(tmp)   
                return
            else:            
                if date_rule.version=='week_start':
                    onNthWeekDay=date_rule.weekDay
                    tmp=TimeBasedRules(onNthWeekDay=onNthWeekDay,
                              onHour=onHour,
                              onMinute=onMinute,
                              func=func)
                    self.scheduledFunctionList.append(tmp)
                    return
                elif date_rule.version=='week_end':
                    onNthWeekDay=-date_rule.weekDay-1
                    tmp=TimeBasedRules(onNthWeekDay=onNthWeekDay,
                              onHour=onHour,
                              onMinute=onMinute,
                              func=func)
                    self.scheduledFunctionList.append(tmp)
                    return
                if date_rule.version=='month_start':
                    onNthMonthDay=date_rule.monthDay
                    tmp=TimeBasedRules(onNthMonthDay=onNthMonthDay,
                              onHour=onHour,
                              onMinute=onMinute,
                              func=func)
                    self.scheduledFunctionList.append(tmp)
                    return
                elif date_rule.version=='month_end':
                    onNthMonthDay=-date_rule.monthDay-1
                    tmp=TimeBasedRules(onNthMonthDay=onNthMonthDay,
                              onHour=onHour,
                              onMinute=onMinute,
                              func=func)
                    self.scheduledFunctionList.append(tmp)
                    return
                     
    #### Request information from IB server 

    def request_data(self,
                  positions  = None,
                  accountDownload= None,
                  reqAccountSummary = None,
                  nextValidId= None,
                  historyData= None,
                  realTimePrice = None,
                  realTimeBars=None,
                  contractDetails= None,
                  marketSnapShot=None,
                  reqAllOpenOrders= None,
                  cancelMktData=None,
                  reqCurrentTime=None,
                  calculateImpliedVolatility=None,
                  waiver=None,
                  waitForFeedbackinSeconds=30,
                  repeat=3):
        self.log.notset(__name__+'::request_data')                          
        exit_untill_completed=0
        while(exit_untill_completed<=3):       
            if exit_untill_completed==0:
                all_req_info=self.create_end_check_list( \
                      positions  = positions,
                      accountDownload= accountDownload,
                      reqAccountSummary= reqAccountSummary,
                      nextValidId= nextValidId,
                      historyData= historyData,
                      realTimePrice = realTimePrice,
                      realTimeBars = realTimeBars,
                      contractDetails= contractDetails,
                      marketSnapShot= marketSnapShot,
                      reqAllOpenOrders= reqAllOpenOrders,
                      cancelMktData= cancelMktData,
                      reqCurrentTime=reqCurrentTime,
                      calculateImpliedVolatility=calculateImpliedVolatility,
                      waiver=waiver)
                self.req_info_from_server(all_req_info)            
            elif exit_untill_completed>=1:
                self.log.error(__name__+'::request_data: Re-send request info')
                #self.display_end_check_list()
                new_list=self.search_in_end_check_list(notDone=True,output_version='list')
                self.log.debug(__name__+'::request_data:NotDone in self.end_check_list')
                for ct in new_list:
                    self.log.debug(__name__+'::reqeust_data:'+str(ct)+' '+str(new_list[ct]))
                    #print (new_list[ct].reqId)
                    #print (new_list[ct].reqType)
                    if new_list[ct].reqType=='realTimePrice':
                        self.cancelMktData(new_list[ct].reqId)
                        self.log.debug(__name__+'::request_data: cancelMktData Id='+str(new_list[ct].reqId))
                # re-send request info                
                self.req_info_from_server(new_list)  
                
            # continuously check if all requests have received responses 
            while (self.req_info_from_server_if_all_completed()==False) :
                if self.runMode!= 'test_mode':
                    time.sleep(0.1)            
                self.processMessages()
                if self.check_timer(waitForFeedbackinSeconds)==True:
                    break
            
            # if receive data successfull, exit to loop
            # else, prepare to re-submit
            if self.req_info_from_server_if_all_completed()==True:
                self.log.debug(__name__+'::request_data: all responses are received')
                break
            else:
                # wait for 5 seconds
                for i in range(50):
                    time.sleep(0.1)            
                    self.processMessages()
                # prepare to re-submit    
                exit_untill_completed=exit_untill_completed+1
  
        # if tried many times, exit; if successfully done, return
        if exit_untill_completed>repeat:
            self.log.error(__name__+'::request_data: Tried many times, but Failed')
            self.end()
        self.log.debug(__name__+'::req_info_from_server: COMPLETED')


    def create_end_check_list(self,
                      positions  = None,
                      accountDownload= None,
                      reqAccountSummary =None, 
                      nextValidId= None,
                      historyData= None,
                      realTimePrice = None,
                      realTimeBars = None,
                      contractDetails= None,
                      marketSnapShot=None,
                      reqAllOpenOrders =None,
                      cancelMktData = None,
                      reqCurrentTime= None,
                      calculateImpliedVolatility= None,
                      waiver=None):
        self.log.notset(__name__+'::create_end_check_list')                          
        end_check_list={}
        end_check_list_id=0
        if positions  == True:
            end_check_list[end_check_list_id]=\
                    EndCheckListClass(status='Created',
                                      reqType='positions')  
            end_check_list_id=end_check_list_id+1
        if accountDownload!=None and accountDownload !=False:
            if type(accountDownload)==type(''):
                end_check_list[end_check_list_id]=\
                        EndCheckListClass(status='Created',
                                          reqType='accountDownload',
                                          input_parameters=accountDownload)
                end_check_list_id=end_check_list_id+1
            elif type(accountDownload)==type((0,0)):
                end_check_list[end_check_list_id]=\
                        EndCheckListClass(status='Created',
                                          reqType='reqAccountSummary',
                                          input_parameters='all')
                end_check_list_id=end_check_list_id+1
            else:
                self.log.error(__name__+'::create_end_check_list: EXIT, cannot\
                handle accountDownload='+str(accountDownload))
                self.end()
        if reqAccountSummary!=None and reqAccountSummary !=False:
            end_check_list[end_check_list_id]=\
                    EndCheckListClass(status='Created',
                                      reqType='reqAccountSummary',
                                      input_parameters='all')
            end_check_list_id=end_check_list_id+1

        if nextValidId== True:
            end_check_list[end_check_list_id]=\
                    EndCheckListClass(status='Created',
                                      reqType='nextValidId')            
            end_check_list_id=end_check_list_id+1
        if historyData!=None and historyData!=False: 
            if type(historyData[0])==tuple:
                reqHistList=[]
                for ct in historyData:
                    tmp=ReqHistClass(security=ct[0],
                                     barSize=ct[1],
                                     goBack=ct[2],
                                     endTime=self.get_datetime())
                    reqHistList.append(tmp)
            else:
                reqHistList=historyData
            for ct in reqHistList:             
                end_check_list[end_check_list_id]=EndCheckListClass(\
                                            status='Created',
                                            input_parameters=ct,
                                            return_result=pd.DataFrame(),
                                            reqType='historyData',
                                            security=ct.security)                                            
                end_check_list_id=end_check_list_id+1
        if realTimePrice != False and realTimePrice != None: 
            if realTimePrice!='Default':            
                for security in realTimePrice:
                    end_check_list[end_check_list_id]=EndCheckListClass(\
                                                    status='Created',
                                                    input_parameters=security,
                                                    reqType='realTimePrice',
                                                    security=security)
                    end_check_list_id=end_check_list_id+1
            else:
                for security in self.qData.data:
                    end_check_list[end_check_list_id]=EndCheckListClass(\
                                                    status='Created',
                                                    input_parameters=security,
                                                    reqType='realTimePrice',
                                                    security=security)
                    end_check_list_id=end_check_list_id+1

        if realTimeBars != False and realTimeBars != None: 
            if realTimeBars!='Default':
                if type(realTimeBars)!=list:
                    end_check_list[end_check_list_id]=EndCheckListClass(\
                                                    status='Created',
                                                    input_parameters=realTimeBars,
                                                    reqType='realTimeBars',
                                                    security=realTimeBars)
                    end_check_list_id=end_check_list_id+1
                else:                    
                    for security in realTimeBars:
                        end_check_list[end_check_list_id]=EndCheckListClass(\
                                                        status='Created',
                                                        input_parameters=security,
                                                        reqType='realTimeBars',
                                                        security=security)
                        end_check_list_id=end_check_list_id+1
            else:
                for security in self.qData.data:
                    end_check_list[end_check_list_id]=EndCheckListClass(\
                                                    status='Created',
                                                    input_parameters=security,
                                                    reqType='realTimeBars',
                                                    security=security)
                    end_check_list_id=end_check_list_id+1
                
        if contractDetails!= False and contractDetails!= None:
            for security in contractDetails:
                end_check_list[end_check_list_id]=EndCheckListClass(\
                                                status='Created',
                                                input_parameters=security,
                                                return_result=pd.DataFrame(),
                                                reqType='contractDetails',
                                                security=security)
                end_check_list_id=end_check_list_id+1
        if marketSnapShot != False and marketSnapShot != None:             
            for security in marketSnapShot:
                end_check_list[end_check_list_id]=EndCheckListClass(\
                                                status='Created',
                                                input_parameters=security,
                                                reqType='marketSnapShot',
                                                security=security)
                end_check_list_id=end_check_list_id+1
        if reqAllOpenOrders != None:             
            end_check_list[end_check_list_id]=EndCheckListClass(\
                                            status='Created',
                                            reqType='reqAllOpenOrders')
            end_check_list_id=end_check_list_id+1

        if cancelMktData != None:   
            for security in cancelMktData:
                end_check_list[end_check_list_id]=EndCheckListClass(\
                                                status='Created',
                                                input_parameters=security,
                                                reqType='cancelMktData',
                                                security=security)
                end_check_list_id=end_check_list_id+1
        if reqCurrentTime != None:
            end_check_list[end_check_list_id]=EndCheckListClass(\
                                            status='Created',
                                            reqType='reqCurrentTime')
            end_check_list_id=end_check_list_id+1 
        
        if calculateImpliedVolatility !=None:
            security,oPrice, uPrice=calculateImpliedVolatility
            end_check_list[end_check_list_id]=EndCheckListClass(\
                                            status='Created',
                                            input_parameters=(oPrice, uPrice),
                                            reqType='calculateImpliedVolatility',
                                            security=security)
            

        if waiver!=None and waiver!=False:
            for ct in waiver:
                Found=False
                for item in end_check_list:
                    if end_check_list[item].reqType==ct:
                        Found=True
                        end_check_list[item].waiver=True
                if Found==False:
                    self.log.error(__name__+'::create_end_check_list: EXIT, cannot handle waiver='+str(ct))
                    self.end()            
        return end_check_list
            
    def req_info_from_server(self, list_requests):
        self.log.debug(__name__+'::req_info_from_server: Request the following info to server')
        self.end_check_list=list_requests
        
        for ct in self.end_check_list:
            self.end_check_list[ct].status='Submitted'
            if self.end_check_list[ct].reqType=='positions':
                self.log.debug(__name__+'::req_info_from_server: requesting open positions info from IB')
                self.reqPositions()                            # request open positions
            elif self.end_check_list[ct].reqType=='reqCurrentTime':
                self.log.debug(__name__+'::req_info_from_server: requesting IB server time')
                self.reqCurrentTime()                            # request open positions
            elif self.end_check_list[ct].reqType=='reqAllOpenOrders':
                self.log.debug(__name__+'::req_info_from_server: requesting allOpenOrders from IB')
                self.reqAllOpenOrders()                            # request all open orders
            elif self.end_check_list[ct].reqType=='accountDownload':
                self.log.debug(__name__+'::req_info_from_server: requesting to update account=%s info from IB' %(self.end_check_list[ct].input_parameters,))
                self.reqAccountUpdates(True,self.end_check_list[ct].input_parameters)  # Request to update account info
            elif self.end_check_list[ct].reqType=='reqAccountSummary':
                #self.log.error(__name__+'::req_info_from_server: EXIT, reqAccountSummary is not ready')
                #self.end()
                self.log.debug(__name__+'::req_info_from_server: reqAccountSummary account=%s, reqId=%i' %(self.end_check_list[ct].input_parameters,self.nextId))
                self.reqAccountSummary(self.nextId, 'All', 'TotalCashValue,GrossPositionValue,NetLiquidation')                               
                self.end_check_list[ct].reqId=self.nextId                                
                self.nextId += 1  # Prepare for next request

            elif self.end_check_list[ct].reqType=='nextValidId':                
                self.log.debug(__name__+'::req_info_from_server: requesting nextValidId')
                self.nextId=None                
                self.reqIds(0)
            elif self.end_check_list[ct].reqType=='historyData':
                self.log.debug(__name__ + '::req_info_from_server: Req hist: %s' %(self.end_check_list[ct].input_parameters, ))                   
                self.end_check_list[ct].reqId=self.nextId 
                self.receivedHistFlag=False
                self.reqHistoricalData(self.nextId, 
                                       create_contract(self.end_check_list[ct].input_parameters.security),
                                       self.end_check_list[ct].input_parameters.endTime,
                                       self.end_check_list[ct].input_parameters.goBack,
                                       self.end_check_list[ct].input_parameters.barSize,
                                       self.end_check_list[ct].input_parameters.whatToShow,
                                       self.end_check_list[ct].input_parameters.useRTH,
                                       self.end_check_list[ct].input_parameters.formatDate)
                self.nextId += 1  # Prepare for next request
                if self.runMode!= 'test_mode':
                    time.sleep(0.1)

            elif self.end_check_list[ct].reqType=='realTimePrice':
                self.log.notset(__name__+'::req_info_from_server: '+str(self.end_check_list[ct]))

                sec=search_security_in_Qdata(self.qData,self.end_check_list[ct].security, self.logLevel)              
                # put security and reqID in dictionary for fast acess
                # it is keyed by both security and reqId
                self.realTimePriceRequestedList[sec]=self.nextId
                self.realTimePriceRequestedList[self.nextId]=sec

                if self.runMode!='test_run':               
                    self.qData.data[sec].ask_price=-1 # None: not requested yet, 
                    self.qData.data[sec].bid_price=-1 #-1: requested but no real time
                    self.qData.data[sec].ask_size=-1
                    self.qData.data[sec].bid_size=-1
                    self.qData.data[sec].last_traded=-1
                self.reqMktData(self.nextId, create_contract(self.end_check_list[ct].security),'233',False) # Send market data requet to IB server
                self.end_check_list[ct].reqId=self.nextId                                
                self.nextId += 1  # Prepare for next request
            
            elif self.end_check_list[ct].reqType=='cancelMktData':
                sec=search_security_in_Qdata(self.qData,self.end_check_list[ct].security, self.logLevel)
                reqId=self.realTimePriceRequestedList[sec]
                self.log.debug(__name__+'::req_info_from_server: cancelMktData: ' 
                            +str(self.end_check_list[ct].security) + ' '
                            +'reqId='+str(reqId))
                self.cancelMktData(reqId)
                self.qData.data[sec].ask_price=-1
                self.qData.data[sec].bid_price=-1
                self.qData.data[sec].ask_size=-1
                self.qData.data[sec].bid_size=-1
                           
            elif self.end_check_list[ct].reqType=='realTimeBars':
                sec=self._save_info(self.end_check_list[ct].security)
                self.reqRealTimeBars(self.nextId, 
                                     create_contract(self.end_check_list[ct].security),
                                     5, 'ASK', False) # Send market data requet to IB server
                self.end_check_list[ct].reqId=self.nextId                                
                self.log.debug(__name__+'::req_info_from_server:requesting realTimeBars: ' 
                            +str(self.end_check_list[ct].security) + ' '
                            +'reqId='+str(self.nextId))
                self.nextId += 1  # Prepare for next request
            elif self.end_check_list[ct].reqType=='contractDetails':
                self.reqContractDetails(self.nextId, create_contract(self.end_check_list[ct].security))
                self.end_check_list[ct].reqId=self.nextId                                
                self.log.debug(__name__+'::req_info_from_server: reqesting contractDetails '\
                                    +str(self.end_check_list[ct])+' reqId='+str(self.nextId))
                self.nextId += 1  # Prepare for next request
            elif self.end_check_list[ct].reqType=='marketSnapShot':
                sec=self.end_check_list[ct].security
                search_security_in_Qdata(self.qData,sec, self.logLevel).reqMarketSnapShotId=self.nextId
                self.reqMktData(self.nextId, create_contract(self.end_check_list[ct].security),'',True) # Send market data requet to IB server
                self.end_check_list[ct].reqId=self.nextId                                
                self.log.debug(__name__+'::req_info_from_server: requesting market snapshot: '+str(self.end_check_list[ct].security)+' reqId='+str(self.nextId))
                self.nextId += 1  # Prepare for next request
            elif self.end_check_list[ct].reqType=='calculateImpliedVolatility':
                # put security and reqID in dictionary for fast acess
                # it is keyed by both security and reqId
                self.realTimePriceRequestedList[self.end_check_list[ct].security]=self.nextId
                self.realTimePriceRequestedList[self.nextId]=self.end_check_list[ct].security

                self.calculateImpliedVolatility(self.nextId, 
                create_contract(self.end_check_list[ct].security), 
                self.end_check_list[ct].input_parameters[0], 
                self.end_check_list[ct].input_parameters[1])

                self.end_check_list[ct].reqId=self.nextId                                
                self.log.info(__name__+'::req_info_from_server: calculateImpliedVolatility: '\
                +str(self.end_check_list[ct].security)+' reqId='+str(self.nextId)\
                +' optionPrice='+str(self.end_check_list[ct].input_parameters[0])\
                +' uderlyingPrice='+str(self.end_check_list[ct].input_parameters[1]))
                self.nextId += 1  # Prepare for next request               
            else:
                self.log.error(__name__+'::req_info_from_server: EXIT, cannot handle reqType='+self.end_check_list[ct].reqType)
                self.end()

        for ct in self.end_check_list:
            self.log.debug(__name__+'::req_info_from_server:'+str(ct)+' '+str(self.end_check_list[ct]))        
        self.set_timer()

    def req_info_from_server_if_all_completed(self):
        for ct in self.end_check_list:
            self.log.notset(__name__+'::req_info_from_server_if_all_completed: '+str(self.end_check_list[ct]))
            if self.end_check_list[ct].reqType=='realTimePrice':
                sec= self.end_check_list[ct].security
                if sec.secType!='IND':
                    if self.qData.data[search_security_in_Qdata(self.qData,sec, self.logLevel)].ask_price>=0.01 \
                            and self.qData.data[search_security_in_Qdata(self.qData,sec, self.logLevel)].bid_price>=0.01:
                        self.end_check_list[ct].status='Done'
                else: # index will never received bid ask price. only last_traded
                    if self.qData.data[search_security_in_Qdata(self.qData,sec, self.logLevel)].last_traded>=0.01:
                        self.end_check_list[ct].status='Done'
                    
            elif self.end_check_list[ct].reqType=='realTimeBars':
                self.end_check_list[ct].status='Done'
            elif self.end_check_list[ct].reqType=='reqCurrentTime':
                if self.recordedServerUTCtime!=None:
                    self.end_check_list[ct].status='Done'
            elif self.end_check_list[ct].reqType=='nextValidId':
                if self.nextValidId!=None:
                    self.end_check_list[ct].status='Done'
            elif self.end_check_list[ct].reqType=='reqAllOpenOrders':
                self.end_check_list[ct].status='Done'
            elif self.end_check_list[ct].reqType=='cancelMktData':
                self.end_check_list[ct].status='Done'

        for ct in self.end_check_list:
            if self.end_check_list[ct].status!='Done' and self.end_check_list[ct].waiver!=True:
                return False                
        return True
 

