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
from_symbol_to_security, calendars, \
TimeBasedRules,search_security_in_Qdata, ReqData

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
        elif errorCode == 202: # cancel order is confirmed
            self.end_check_list.loc[errorId, 'status'] = 'Done'
            
        elif errorCode in [399, 504, 165]: # No action, just show error message
            self.log.error(__name__ + ':errorId = %s, errorCode = %s, error message: %s' %(str(errorId), str(errorCode), errorString))

        elif errorCode >= 110 and errorCode <= 449:
            self.log.error(__name__ + ':EXIT errorId = %s, errorCode = %s, error message: %s' %(str(errorId), str(errorCode), errorString))
            self.log.error(__name__ + ':EXIT IBridgePy version = %s' %(str(self.versionNumber),))
            exit()
          
        elif errorCode in [1100, 1101, 1102]:
            if errorCode==1100:
                self.connectionGatewayToServer=False
            elif errorCode in [1101, 1102]:
                self.connectionGatewayToServer=True
        else:
            self.log.error(__name__ + ':EXIT errorId = %s, errorCode = %s, error message: %s' %(str(errorId), str(errorCode), errorString))
            self.log.error(__name__ + ':EXIT IBridgePy version= %s' %(str(self.versionNumber),))
            exit()               
            
    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the showTimeZone from MarketManager
        """
        self.log.notset(__name__+'::currentTime')
        self.recordedServerUTCtime=tm # float, utc number
        self.recordedLocalTime = dt.datetime.now() # a datetime, without tzinfo
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqCurrentTime']['reqId']      
        self.end_check_list.loc[reqId, 'status'] = 'Done'
                                              
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
            tp=self.end_check_list[self.end_check_list['status'] != 'Done']
            self.log.error(str(tp))            
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
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqIds']['reqId']      
        self.end_check_list.loc[reqId, 'status'] = 'Done'
                                                 
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

        # if reqId in self.end_check_list, then, mark it as Done
        # else        
        # reqId may not in self.end_check_list anymore
        # So, record reqId in self.realTimePriceRequestedList
        if reqId in self.end_check_list.index:
            self.end_check_list.loc[reqId, 'status'] = 'Done'
            security = self.end_check_list.loc[reqId, 'reqData'].param['security']
        else:
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
            self.update_last_price_in_positions(price, security)
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
        elif tickType == 3: # Ask Size
            self.qData.data[security].ask_size = size
            #self.update_DataClass(security, 'ask_size_flow', size)  
        elif tickType == 5: # Last Size
            self.qData.data[security].size = size
            #self.update_DataClass(security, 'last_size_flow', size)
        elif tickType == 8: # Volume
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
        sec = self.end_check_list.loc[reqId, 'reqData'].param['security']
        barSize = self.end_check_list.loc[reqId, 'reqData'].param['barSize']
        
        if self.receivedHistFlag == False:
            self.log.debug(__name__+'::historicalData: Received 1st row %s %s'%(sec, barSize))
            self.receivedHistFlag=True
             
        if 'finished' in str(date):
            self.end_check_list.loc[reqId, 'status'] = 'Done'       
            
            #if the returned security is in self.qData.data, put the historicalData into self.qData.data
            # else, add the new security in self.qData.data
            self.log.notset(__name__ + '::historicalData: finished req hist data for ' + str(sec))
            self.log.notset('First line is ')
            self.log.notset(str(self.qData.data[sec].hist[barSize].iloc[0]))
            self.log.notset('Last line is ')
            self.log.notset(str(self.qData.data[sec].hist[barSize].iloc[-1]))
            
        else:
            if self.end_check_list.loc[reqId, 'reqData'].param['formatDate']==1:
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

            if date in self.qData.data[sec].hist[barSize].index:
                self.qData.data[sec].hist[barSize]['open'][date]=price_open
                self.qData.data[sec].hist[barSize]['high'][date]=price_high
                self.qData.data[sec].hist[barSize]['low'][date]=price_low
                self.qData.data[sec].hist[barSize]['close'][date]=price_close
                self.qData.data[sec].hist[barSize]['volume'][date]=volume
            else:
                newRow = pd.DataFrame({'open':price_open,'high':price_high,
                                       'low':price_low,'close':price_close,
                                       'volume':volume}, index = [date])
                self.qData.data[sec].hist[barSize] = self.qData.data[sec].hist[barSize].append(newRow)

    def realtimeBar(self, reqId, time, price_open, price_high, price_low, price_close, volume, wap, count):
        """
        call back function from IB C++ API
        return realTimebars for requested security every 5 seconds
        """
        self.log.debug(__name__+'::realtimeBar: reqId='+str(reqId)+','+str(dt.datetime.fromtimestamp(time)))
        if reqId in self.end_check_list.index:
            self.end_check_list.loc[reqId, 'status'] = 'Done'
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

    def openOrderEnd(self):
        self.log.debug(__name__+'::openOrderEnd')
        reqId = self.end_check_list[(self.end_check_list['reqType'] == 'reqAllOpenOrders') | 
                                    (self.end_check_list['reqType'] == 'reqOpenOrders') |
                                    (self.end_check_list['reqType'] == 'reqAutoOpenOrders')]['reqId']      
        self.end_check_list.loc[reqId, 'status'] = 'Done'      
        
    def positionEnd(self):
        self.log.notset(__name__+'::positionEnd: all positions recorded')
        reqId = self.end_check_list[self.end_check_list['reqType'] == 'reqPositions']['reqId']
        self.end_check_list.loc[reqId, 'status'] = 'Done'
           
    def tickSnapshotEnd(self, reqId):
        self.log.notset(__name__+'::tickSnapshotEnd: '+str(reqId))
                                 
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
        self.end_check_list_result[reqId] = self.end_check_list_result[reqId].append(newRow)

    def contractDetailsEnd(self, reqId):
        '''
        IB callback function to receive the ending flag of contract info
        '''
        self.log.debug(__name__+'::contractDetailsEnd:'+str(reqId))
        self.end_check_list.loc[reqId, 'status'] = 'Done'

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
        self.request_data(ReqData.reqMktData(security, waiver=waiver))


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

    def _save_info_toBeDeleted(self, security):  
        self.log.debug(__name__+'::_save_info')
        #sec=search_security_in_Qdata(self.qData, security, self.logLevel)               
        # put security and reqID in dictionary for fast acess
        # it is keyed by both security and reqId
        self.realTimePriceRequestedList[security] = self.nextId
        self.realTimePriceRequestedList[self.nextId] = security
    
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
        elif cntrct.secType=='FUT':
            return cntrct.secType+','+\
            str(cntrct.symbol)+','+\
            str(cntrct.primaryExchange)+','+\
            str(cntrct.exchange)+','+\
            str(cntrct.currency)+','+\
            str(cntrct.expiry)
        else:
            return cntrct.secType+','+\
            str(cntrct.symbol)+','+\
            str(cntrct.primaryExchange)+','+\
            str(cntrct.exchange)+','+\
            str(cntrct.currency)

    ####### API functions ###################
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

    def get_contract_details(self,  secType,
                                    symbol,
                                    currency='USD',
                                    exchange='',
                                    primaryExchange='',
                                    expiry='',
                                    strike=-1,
                                    right='',
                                    multiplier=''):
        security = self.superSymbol(secType=secType, symbol=symbol, currency=currency,
                        exchange=exchange, primaryExchange=primaryExchange,
                        expiry=expiry, strike=strike, right=right, multiplier=multiplier)
        self.request_data(ReqData.reqContractDetails(security))
        if len(self.end_check_list_result) == 1:
            for ct in self.end_check_list_result:
                return self.end_check_list_result[ct]


        
    def request_historical_data(self, security,
                                        barSize,
                                        goBack,
                                        endTime='',
                                        whatToShow='',
                                        useRTH=1,
                                        formatDate=2,
                                        waitForFeedbackinSeconds=30):                                  
        self.request_data(ReqData.reqHistoricalData(security, barSize, goBack,
                                                    endTime, whatToShow, useRTH,
                                                    formatDate))      
        return self.qData.data[security].hist[barSize]                                  
            
    def symbol(self, str_security):
        self.log.notset(__name__+'::symbol:'+str_security)  
        a_security=from_symbol_to_security(str_security, self.logLevel)
        re=search_security_in_Qdata(self.qData, a_security, self.logLevel)  
        #self.build_security_in_positions(a_security, accountCode='all')
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
                    multiplier='',
                    includeExpired=False):
        self.log.notset(__name__+'::superSymbol')  
        a_security= Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange, expiry=expiry,
                    strike=strike, right=right, multiplier=multiplier, includeExpired=includeExpired)  
        re=search_security_in_Qdata(self.qData, a_security, self.logLevel)
        #self.build_security_in_positions(a_security, accountCode='all')
        return re
           
            

    def show_nextId(self):
        return self.nextId
        
    def show_real_time_price(self, security, version):
        self.log.notset(__name__+'::show_real_time_price')                          
        version=priceNameChange[version]
        if security not in self.realTimePriceRequestedList:
            self.request_data(ReqData.reqMktData(security, waiver=True))    
        if hasattr(self.qData.data[security], version):
            return getattr(self.qData.data[security], version)
        else:
            self.log.error(__name__+'::show_real_time_price: EXIT, cannot handle version='+version)
            self.end()

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
    def req_info_from_server_if_all_completed(self):
        self.log.notset(__name__+'::req_info_from_server_if_all_completed')
        for idx in self.end_check_list.index:
            if self.end_check_list.loc[idx, 'status'] !='Done' and self.end_check_list.loc[idx, 'waiver'] != True:
                return False                
        return True
 
    def request_data(self, *args):
        self.log.notset(__name__+'::request_data')    

        # change args to a pandas dataFrame 
        # index is reqId
        reqList = pd.DataFrame()
        for ct in args:
            ct.reqId = self.nextId
            self.nextId += 1
            newRow = pd.DataFrame({'reqId':ct.reqId, 'status':ct.status, 
                                   'waiver':ct.waiver, 'reqData':ct, 
                                   'reqType':ct.reqType}, index=[ct.reqId])
            reqList = reqList.append(newRow)
                      
        exit_untill_completed=0
        while(exit_untill_completed<=3):       
            if exit_untill_completed==0:
                self.req_info_from_server(reqList)            
            elif exit_untill_completed>=1:
                self.log.error(__name__+'::request_data: Re-send request info')
                newReqList=reqList[reqList['status'] == 'submitted']
                self.log.debug(__name__+'::request_data: reqData is not successful')
                for idx in newReqList.index:
                    self.log.debug(__name__+'::reqeust_data:'+str(newReqList.loc[idx]['reqData']))

                # re-send request info                
                self.req_info_from_server(newReqList)  
                
            # continuously check if all requests have received responses 
            while (self.req_info_from_server_if_all_completed()==False) :
                if self.runMode!= 'test_mode':
                    time.sleep(0.1)            
                self.processMessages()
                if self.check_timer(self.waitForFeedbackinSeconds)==True:
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
        if exit_untill_completed > self.repeat:
            self.log.error(__name__+'::request_data: Tried many times, but Failed')
            self.end()
        self.log.debug(__name__+'::req_info_from_server: COMPLETED')
        

        
    def req_info_from_server(self, reqData):
        self.log.debug(__name__+'::req_info_from_server: Request the following info to server')
        self.end_check_list = reqData
        self.end_check_list_result = {}
        
        for idx in self.end_check_list.index:
            self.end_check_list.loc[idx, 'status']='Submitted'
            if self.end_check_list.loc[idx, 'reqType'] == 'reqPositions':
                self.log.debug(__name__+'::req_info_from_server: requesting open positions info from IB')
                self.reqPositions()                            # request open positions

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqCurrentTime':
                self.log.debug(__name__+'::req_info_from_server: requesting IB server time')
                self.reqCurrentTime()                            # request open positions

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqAllOpenOrders':
                self.log.debug(__name__+'::req_info_from_server: requesting reqAllOpenOrders from IB')
                self.reqAllOpenOrders()                            # request all open orders

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqAccountUpdates':
                accountCode = self.end_check_list.loc[idx, 'reqData'].param['accountCode']
                subscribe = self.end_check_list.loc[idx, 'reqData'].param['subscribe']
                self.log.debug(__name__+'::req_info_from_server: requesting to update account=%s info from IB' %(accountCode,))
                self.reqAccountUpdates(subscribe, accountCode )  # Request to update account info

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqAccountSummary':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                group = self.end_check_list.loc[idx, 'group']
                tag = self.end_check_list.loc[idx, 'tag']
                self.log.debug(__name__+'::req_info_from_server: reqAccountSummary account=%s, reqId=%i' %(group, reqId))
                self.reqAccountSummary(reqId, group, tag)                               

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqIds':                
                self.log.debug(__name__+'::req_info_from_server: requesting reqIds')
                self.nextId = None                
                self.reqIds(0)
                
            elif self.end_check_list.loc[idx, 'reqType'] == 'reqHistoricalData':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                security = self.end_check_list.loc[idx, 'reqData'].param['security']
                endTime = self.end_check_list.loc[idx, 'reqData'].param['endTime']
                goBack = self.end_check_list.loc[idx, 'reqData'].param['goBack']
                barSize = self.end_check_list.loc[idx, 'reqData'].param['barSize']
                whatToShow = self.end_check_list.loc[idx, 'reqData'].param['whatToShow']
                useRTH = self.end_check_list.loc[idx, 'reqData'].param['useRTH']
                formatDate = self.end_check_list.loc[idx, 'reqData'].param['formatDate']
                self.qData.data[security].hist[barSize] = pd.DataFrame()
                self.log.debug(__name__ + '::req_info_from_server: Req hist: %s %s' %(str(self.end_check_list.loc[idx, 'reqData'].param), str(security)))                   
                self.receivedHistFlag=False
                self.reqHistoricalData(reqId, 
                                       create_contract(security),
                                       endTime,
                                       goBack,
                                       barSize,
                                       whatToShow,
                                       useRTH,
                                       formatDate)
                if self.runMode!= 'test_mode':
                    time.sleep(0.1)

            elif self.end_check_list.loc[idx, 'reqType'] == 'reqMktData':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                security = self.end_check_list.loc[idx, 'reqData'].param['security']
                genericTickList = self.end_check_list.loc[idx, 'reqData'].param['genericTickList']
                snapshot = self.end_check_list.loc[idx, 'reqData'].param['snapshot']                              
                self.log.debug(__name__+'::req_info_from_server: request realTimePrice %s %s %s' %(str(security), genericTickList, str(snapshot)))
              
                # put security and reqID in dictionary for fast acess
                # it is keyed by both security and reqId
                self.realTimePriceRequestedList[security] = reqId
                self.realTimePriceRequestedList[reqId] = security

                if self.runMode!='test_run':               
                    self.qData.data[security].ask_price=-1 # None: not requested yet, 
                    self.qData.data[security].bid_price=-1 #-1: requested but no real time
                    self.qData.data[security].ask_size=-1
                    self.qData.data[security].bid_size=-1
                    self.qData.data[security].last_traded=-1
                self.reqMktData(reqId, create_contract(security),
                                genericTickList,snapshot) # Send market data requet to IB server
            
            elif self.end_check_list.loc[idx, 'reqType'] == 'cancelMktData':
                security = self.end_check_list.loc[idx, 'reqData'].param['security']
                reqId = self.realTimePriceRequestedList[security]
                self.log.debug(__name__+'::req_info_from_server: cancelMktData: ' 
                            +str(security) + ' '
                            +'reqId='+str(reqId))
                self.cancelMktData(reqId)
                self.qData.data[security].ask_price=-1
                self.qData.data[security].bid_price=-1
                self.qData.data[security].ask_size=-1
                self.qData.data[security].bid_size=-1
                self.qData.data[security].size=-1
                           
            elif self.end_check_list.loc[idx, 'reqType'] == 'reqRealTimeBars':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                security = self.end_check_list.loc[idx, 'reqData'].param['security']
                barSize = self.end_check_list.loc[idx, 'reqData'].param['barSize']
                whatToShow = self.end_check_list.loc[idx, 'reqData'].param['whatToShow']
                useRTH = self.end_check_list.loc[idx, 'reqData'].param['useRTH']
                self.realTimePriceRequestedList[security] = reqId
                self.realTimePriceRequestedList[reqId] = security
                self.log.debug(__name__+'::req_info_from_server:requesting realTimeBars: ' 
                            +str(security) + ' '
                            +'reqId='+str(reqId))
                self.reqRealTimeBars(reqId, 
                                     create_contract(security),
                                     barSize, whatToShow, useRTH) # Send market data requet to IB server
                               
            elif self.end_check_list.loc[idx, 'reqType'] == 'reqContractDetails':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                security = self.end_check_list.loc[idx, 'reqData'].param['security']
                self.reqContractDetails(reqId, create_contract(security)) 
                self.end_check_list_result[reqId] = pd.DataFrame()                             
                self.log.debug(__name__+'::req_info_from_server: reqesting contractDetails '\
                                    +str(security)+' reqId='+str(reqId))

            elif self.end_check_list.loc[idx, 'reqType'] == 'calculateImpliedVolatility':
                reqId = int(self.end_check_list.loc[idx, 'reqId'])
                security = float(self.end_check_list.loc[idx, 'reqData'].param['security'])
                optionPrice = float(self.end_check_list.loc[idx, 'reqData'].param['optionPrice'])
                underPrice = float(self.end_check_list.loc[idx, 'reqData'].param['underPrice'])

                # put security and reqID in dictionary for fast acess
                # it is keyed by both security and reqId
                self.realTimePriceRequestedList[security] = reqId
                self.realTimePriceRequestedList[reqId] = security

                self.calculateImpliedVolatility(reqId, 
                                                create_contract(security), 
                                                optionPrice, 
                                                underPrice)                               
                self.log.debug(__name__+'::req_info_from_server: calculateImpliedVolatility: '\
                +str(security)+' reqId='+str(reqId)\
                +' optionPrice='+str(optionPrice)\
                +' underPrice='+str(underPrice))
              
            else:
                self.log.error(__name__+'::req_info_from_server: EXIT, cannot handle reqType=' + self.end_check_list.loc[idx, 'reqType'])
                self.end()
        self.set_timer()
        