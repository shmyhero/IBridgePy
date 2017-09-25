from IBridgePy import IBCpp
import datetime as dt
import pandas as pd
import numpy as np
import os
from BasicPyLib.Printable import PrintableClass
from BasicPyLib.FiniteState import FiniteStateClass
import pytz
from sys import exit

    
stockList = pd.read_csv(str(os.path.dirname(os.path.realpath(__file__)))+'/security_info.csv')
def search_security_in_file(secType, symbol, param, waive=False):
    if secType=='CASH':
        if param=='exchange':
            return 'IDEALPRO'
        elif param=='primaryExchange':
            return 'IDEALPRO'
        else:
            error_messages(5, secType + ' ' + symbol + ' ' + param)
    else:
        tmp_df = stockList[(stockList['Symbol'] == symbol)&(stockList['secType'] == secType)]
        if tmp_df.shape[0] == 1:
            exchange = tmp_df['exchange'].values[0]
            primaryExchange=tmp_df['primaryExchange'].values[0]
            if param=='exchange':
                if type(exchange) == float:
                    if secType == 'STK':
                        return 'SMART'
                    #else:
                    #    error_messages(4, secType + ' ' + symbol + ' ' + param)
                else:
                    return exchange
            elif param=='primaryExchange':
                return primaryExchange
            else:
                error_messages(5, secType + ' ' + symbol + ' ' + param)
        elif tmp_df.shape[0] > 1:
            error_messages(3, secType + ' ' + symbol + ' ' + param)
        else:          
            if waive:
                return 'NA'
            error_messages(4, secType + ' ' + symbol + ' ' + param)
        
def error_messages(n, st):
    if n == 1:
        print ('Definition of %s is not clear!' %(st,))
        print ('Please add this security in IBridgePy/security_info.csv')
        exit()
    elif n == 2:
        print ('Definition of %s is not clear!' %(st,))
        print ('Please use superSymbol to define a security')
        print (r'http://www.ibridgepy.com/ibridgepy-documentation/#superSymbol')
        exit()
    elif n == 3:
        print ('Found too many %s in IBridgePy/security_info.csv' %(st,))
        print ('%s must be unique.' %(' '.join(st.split(' ')[:-1]),))
        exit()
    elif n == 4:
        print ('Exchange of %s is missing.' %(' '.join(st.split(' ')[:-1]),))
        print ('Please add this security in IBridgePy/security_info.csv')
        exit()
    elif n == 5:
        print ('%s of %s is missing.' %(st.split(' ')[-1],' '.join(st.split(' ')[:-1])))
        print ('Please add this info in IBridgePy/security_info.csv')
        exit()
    
    
def from_symbol_to_security(s1, logLevel='INFO'):
    if logLevel in ['DEBUG', 'NOTSET']:
        print (__name__+'::from_symbol_to_security:'+s1)
    if ',' not in s1:
        s1='STK,%s,USD' %(s1,)        
    
    secType = s1.split(',')[0].strip()
    symbol=s1.split(',')[1].strip()     
    currency = s1.split(',')[2].strip()
    if secType=='CASH': # 'CASH,EUR,USD'
        exchange = 'IDEALPRO'
        primaryExchange = 'IDEALPRO'
        return Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange)

    elif secType == 'FUT': # 'FUT.ES.USD.201503'
        tmp_df = stockList[(stockList['Symbol'] == symbol)&(stockList['secType'] == 'FUT')]
        if (tmp_df.shape[0] > 0):
            exchange = tmp_df['exchange'].values[0]
            primaryExchange=tmp_df['primaryExchange'].values[0]
        else:
            print ('quantopian::from_symbol_to_security: EXIT, FUT need to specify primaryExchange for %s' %(s1,))
            exit()
        expiry=s1.split(',')[3].strip()
        return Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange, expiry=expiry)

    elif secType == 'OPT': # OPT.AAPL.USD.20150702.133.P.100
        exchange = 'SMART'
        expiry= s1.split(',')[3].strip()
        strike= s1.split(',')[4].strip()
        right= s1.split(',')[5].strip()
        multiplier= s1.split(',')[6].strip()
        tmp_df = stockList[(stockList['Symbol'] == symbol)&(stockList['secType'] == 'STK')]
        if (tmp_df.shape[0] > 0):
            primaryExchange = tmp_df['primaryExchange'].values[0]
            currency = tmp_df['Currency'].values[0]
        else:
            primaryExchange = 'NYSE'
            currency = 'USD'  
        return Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange, expiry=expiry,
                    strike=strike, right=right, multiplier=multiplier)

    elif secType == 'STK':
        exchange = 'SMART'         
        tmp_df = stockList[(stockList['Symbol'] == symbol)&(stockList['secType'] == secType)]
        if (tmp_df.shape[0] > 0):
            primaryExchange = tmp_df['primaryExchange'].values[0]
            return Security(secType=secType, symbol=symbol, currency=currency,
                            exchange=exchange, primaryExchange=primaryExchange)
    elif secType == 'CFD':
        exchange = 'SMART'         
        return Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange)

    elif secType =='IND':
        exchange='SMART'
        tmp_df = stockList[(stockList['Symbol'] == symbol)&(stockList['secType'] == 'IND')]
        if (tmp_df.shape[0] > 0):
            exchange = tmp_df['primaryExchange'].values[0]
            primaryExchange=tmp_df['primaryExchange'].values[0]
        else:
            print ('quantopian::Security: EXIT, IND needs to specify primaryExchange for %s'%(s1,))
            exit()
        return Security(secType=secType, symbol=symbol, currency=currency,
                    exchange=exchange, primaryExchange=primaryExchange)
    error_messages(2, s1)

def from_contract_to_security(a_contract, logLevel='INFO'):
    if logLevel in ['NOTSET', 'DEBUG']:
        print (__name__+'::_from_contract_to_security:')
    ans=Security()
    for para in ['secType', 'symbol', 'primaryExchange', 'exchange',\
    'currency','expiry','strike', 'right', 'multiplier']:
        tmp=getattr(a_contract, para)
        #print (para, tmp)
        if tmp != '':
            setattr(ans, para, tmp)
            
    # It is very interesting to find out that a position from IB server does 
    # have an exchange info, for example, XIV has an exchange of NASDAQ
    # But, that exchange won't work when it is used in the following code.
    # the error message is No definition. 
    # The solution is to add 'SMART' to stocks
    ans.exchange=search_security_in_file(ans.secType,ans.symbol, 'exchange')
    if ans.primaryExchange=='':
        ans.primaryExchange=search_security_in_file(ans.secType,ans.symbol, 'primaryExchange')
    return ans
        
def create_contract(security):
    contract = IBCpp.Contract()
    contract.symbol = security.symbol
    contract.secType = security.secType
    contract.exchange = security.exchange
    contract.currency = security.currency       
    contract.primaryExchange = security.primaryExchange
    contract.includeExpired=security.includeExpired      

    if security.secType=='FUT':
        if security.expiry!='xx':       
            contract.expiry = security.expiry       
    elif security.secType=='OPT':
        if security.expiry!='xx':
            contract.expiry= security.expiry
        if security.strike!='xx':    
            contract.strike= float(security.strike)
        if security.right!='xx':
            contract.right= security.right
        if security.multiplier!='xx':
            contract.multiplier= security.multiplier
    return contract 

def same_security(se_1, se_2):
    return str(se_1)==str(se_2)

class OrderBase():
    #use setup function instead of __init__
    def setup(self, orderType,
                 limit_price=None, # defaut price is None to avoid any misformatted numbers
                 stop_price=None,
                 trailing_amount=None,
                 limit_offset=None,
                 tif='DAY'):
        self.orderType=orderType
        self.limit_price=limit_price
        self.stop_price=stop_price
        self.trailing_amount=trailing_amount
        self.limit_offset=limit_offset
        self.tif=tif
        
    def __str__(self):
        string_output=''
        if self.orderType=='MKT':        
            string_output='MarketOrder,unknown exec price'
        elif self.orderType=='STP':
            string_output='StopOrder, stop_price='+str(self.stop_price)
        elif self.orderType=='LMT':
            string_output='LimitOrder, limit_price='+str(self.limit_price)
        elif self.orderType=='TRAIL LIMIT':
            string_output='TrailStopLimitOrder, stop_price='+str(self.stop_price)\
                            +' trailing_percent='+str(self.trailing_percent)\
                            + ' limit_offset='+str(self.limit_offset)
        else:
            print (__name__+'::OrderBase:EXIT, cannot handle'+self.orderType)
            exit()
        return string_output

class MarketOrder(OrderBase):
    def __init__(self, tif='DAY'):
        self.setup(orderType='MKT', tif=tif)

class StopOrder(OrderBase):
    def __init__(self,stop_price, tif='DAY'):
        self.setup(orderType='STP', stop_price=stop_price, tif=tif)

class LimitOrder(OrderBase):
    def __init__(self,limit_price, tif='DAY'):
        self.setup(orderType='LMT', limit_price=limit_price, tif=tif)
        
class TrailStopLimitOrder(OrderBase):
    def __init__(self, stop_price, trailing_percent, limit_offset, tif='DAY'):
        self.setup(orderType='TRAIL LIMIT',
                   stop_price=stop_price,
                   trailing_amount=trailing_percent,
                   limit_offset=limit_offset,
                   tif=tif)
class LimitOnCloseOrder(OrderBase):
    def __init__(self, limit_price):
        self.setup(orderType='LOC', limit_price=limit_price)
class LimitOnOpenOrder(OrderBase):
    def __init__(self, limit_price):
        self.setup(orderType='LOO', limit_price=limit_price)
         
############## Quantopian compatible data structures
class Security(object):
    def __init__(self,
                secType=None,
                symbol=None,
                currency='USD',
                exchange='', #default value, when IB returns contract 
                primaryExchange='',#default value, when IB returns contract
                expiry=None,
                strike=-1,#default value=0.0, when IB returns contract
                right=None,
                multiplier='',#default value, when IB returns contract 
                includeExpired=False,
                sid=-1,
                security_name=None,
                security_start_date=None,
                security_end_date=None):
        self.secType=secType
        self.symbol=symbol
        self.currency=currency
        self.exchange=exchange
        self.primaryExchange=primaryExchange
        self.expiry=expiry
        self.strike=strike
        self.right=right
        self.multiplier=multiplier
        self.includeExpired=includeExpired
        self.sid=sid
        self.security_name=security_name
        self.security_start_date=security_start_date
        self.security_end_date=security_end_date
        #self.reqRealTimeBarsId = -1
        #self.reqMarketSnapShotId= -1        
                
    def __str__(self):
        if self.secType=='STK' or self.secType=='IND' or self.secType=='CFD':
            string_output=self.secType+','+self.symbol+','+self.currency
        elif self.secType=='FUT':
            string_output='FUTURES,'+self.symbol+','+self.currency+','+str(self.expiry)
        elif self.secType=='CASH':
            string_output='CASH,'+self.symbol+','+self.currency
        elif self.secType=='OPT':
            string_output='OPTION,'+self.symbol+','+self.currency+','+str(self.expiry)+','+str(self.strike)+','+self.right+','+str(self.multiplier)
        else:
            print (__name__+'::security: EXIT, cannot handle secType=',self.secType)
            exit()
        return string_output
        
class ContextClass(PrintableClass):
    def __init__(self, accountCode):
        if type(accountCode)==type((0,0)):
            self.portfolio={}
            for ct in accountCode:
                self.portfolio[ct] = PortofolioClass()       
        else:
            self.portfolio = PortofolioClass()       

class PortofolioClass(PrintableClass):
    def __init__(self, capital_used = 0.0, cash = 0.0, pnl = 0.0, 
                 portfolio_value = 0.0, positions_value = 0.0, returns = 0.0, 
                 starting_cash = 0.0, start_date = dt.datetime.now()):
        self.capital_used = capital_used
        self.cash = cash
        self.pnl = pnl
        self.positions = {}
        self.orderStatusBook= {}
        self.portfolio_value = portfolio_value
        self.positions_value = positions_value
        self.returns = returns
        self.starting_cash = starting_cash
        self.start_date = start_date
        self.performanceTracking={} #key: orderRef
        self.virtualHoldings={} # to calculate strategy balance after an order is filled
        
class PositionClass(PrintableClass):
    def __init__(self, amount=0, cost_basis=0.0, last_sale_price=None, sid=None, accountCode=None):
        self.amount = amount
        self.cost_basis=cost_basis
        self.last_sale_price = last_sale_price
        self.sid=sid
        self.accountCode=accountCode
    def __str__(self):
        return 'accountCode='+self.accountCode+' share='+str(self.amount)+' cost_basis='+str(self.cost_basis)+' last_sale_price='+str(self.last_sale_price)


def search_security_in_Qdata(qData, a_security, logLevel):
    if logLevel=='NOTSET':
        print (__name__+'::search_security_in_Qdata')
    if a_security in qData.data:
        return a_security
    #print (__name__+'::search_security_in_Qdata: Search...')
    for ct in qData.data:
        if same_security(ct, a_security):
            return ct
    # if it is not in Qdata, add it into Qdata
    qData.data[a_security]=DataClass()
    if logLevel in ['DEBUG', 'NOTSET']:
        print (__name__+'::search_security_in_Qdata:Add %s into self.qData.data' %(str(a_security),))
    return a_security            


class QDataClass(object):
    '''
    This is a wrapper to match quantopian's data class
    '''
    def __init__(self, parentTrader):
        self.data={}
        self.parentTrader=parentTrader

    def current(self, security, field):
        if type(security)==list and type(field)!=list:
            ans={}
            for ct in security:
                ans[ct]=self.current_one(ct, field)
            return pd.Series(ans)
        elif type(security)==list and type(field)==list:
            ans={}
            for ct1 in field:
                ans[ct1]={}
                for ct2 in security:
                    ans[ct1][ct2]=self.current_one(ct2, ct1)
            return pd.DataFrame(ans)
        elif type(security)!=list and type(field)==list:
            ans={}
            for ct in field:
                ans[ct]=self.current_one(security, ct)
            return pd.Series(ans)
        else:
            return self.current_one(security, field)
        
    def current_one(self, security, version):
        self.parentTrader.log.notset(__name__+'::current_one')                          
        return self.parentTrader.show_real_time_price(security, version)
    
    def history(self, security, fields, bar_count, frequency):
        if frequency=='1d':
            frequency ='1 day'
            goBack=str(bar_count)+' D'
        elif frequency =='1m':
            frequency ='1 min'
            goBack=str(bar_count*60)+' S' 
        elif frequency=='1 hour':
            goBack=str(int(bar_count/24)+3)+' D'
        else:
            print (__name__+'::history: EXIT, cannot handle frequency=%s'%(str(frequency,)))
            exit()
        if type(security)!=list:
            return self.history_one(security, fields, goBack, frequency)

        else:
            if type(fields)==str:
                ans={}
                for sec in security:
                    ans[sec]=self.history_one(sec, fields, goBack, frequency)
                return pd.DataFrame(ans)
            else:
                ans={}
                for fld in fields:
                    ans[fld]={}
                    for sec in security:
                        ans[fld][sec]=self.history_one(sec, fld, goBack, frequency)
                return pd.Panel(ans)
                
        
    def history_one(self, security, fields, goBack, frequency):
        tmp=self.parentTrader.request_historical_data(security,frequency,goBack)
        tmp['price']=tmp['close']
        tmp['price'].fillna(method='pad')
        return tmp[fields]    
        
class DataClass(PrintableClass):
    '''
    This is original IBridgePy data claass
    self.data=[] and symbols are put into the list
    '''
    def __init__(self,
                 datetime=dt.datetime(2000,1,1,0,0),
                 last_traded = None,
                 open = None,
                 close = None,
                 high = None,
                 low =None,
                 volume = None):        
        self.datetime=datetime # Quatopian
        self.last_traded=last_traded # Quatopian
        self.size = -1
        self.open=open # Quatopian
        self.close=close # Quatopian
        self.high = high # Quatopian
        self.low = low # Quatopian
        self.volume = volume # Quatopian
        #self.daily_open_price = None
        #self.daily_high_price = None
        #self.daily_low_price = None
        #self.daily_prev_close_price = None
        self.bid_price = None #not requested yet
        self.ask_price = None #-1: requested but no real time data yet
        self.bid_size = None
        self.ask_size = None
        self.hist={}
       
        # handle realTimeBars
        self.realTimeBars=np.zeros(shape =(0,9))        
        
        # 0 = record_timestamp
        self.bid_price_flow = np.zeros(shape = (0,2))
        self.ask_price_flow = np.zeros(shape = (0,2))
        self.last_traded_flow = np.zeros(shape = (0,2))
        self.bid_size_flow = np.zeros(shape = (0,2))
        self.ask_size_flow = np.zeros(shape = (0,2))
        self.last_size_flow = np.zeros(shape = (0,2))        
        # 0 = trade timestamp; 1 = price_last; 2 = size_last; 3 = record_timestamp
        self.RT_volume = np.zeros(shape = (0,4))
        self.contractDetails=None
        
        # for option 
        self.delta=None
        self.gamma=None
        self.vega=None
        self.theta=None               
        self.impliedVol=None
        self.pvDividend=None
        self.undPrice=None    #price of underlying security of the option           
               
    def update(self,time_input):
        self.datetime=time_input
        self.price=self.hist_bar['close'][-1]
        self.close_price=self.hist_bar['close'][-1]
        self.high=self.hist_bar['high'][-1]
        self.low=self.hist_bar['low'][-1]
        self.volume=self.hist_bar['volume'][-1]
        self.open_price=self.hist_bar['open'][-1]
        self.hist_daily['high'][-1]=self.daily_high_price
        self.hist_daily['low'][-1]=self.daily_low_price
        self.hist_daily['close'][-1]=self.price
    
    def __str__(self):
        return 'Ask= %f; Bid= %f; Open= %f; High= %f; Low= %f; Close= %f; lastUpdateTime= %s' \
            %(self.ask_price,self.bid_price,self.open, self.high, self.low,self.close, str(self.datetime))

class HistClass(object):
    def __init__(self, security=None, period=None,status=None):
        self.status=status
        self.security=security
        self.period=period
        self.hist=pd.DataFrame(columns=['open','high','low','close','volume'])


class OrderClass(object):
    def __init__(self,orderId=None, created=None, parentOrderId = None, stop = None, 
                 limit = None, amount = 0, sid = None, filled = 0,
                 stop_reached = False, limit_reached = False, commission = None,
                 remaining = 0, status = 'na', contract = None, order = None, 
                 orderstate = None, avgFillPrice=0.0, filledTime=None):
        self.orderId=orderId
        self.parentOrderId = parentOrderId
        self.created=created# the time when this order is created.
        self.stop=stop
        self.limit=limit
        self.amount=amount
        self.sid=sid
        self.filled=filled
        self.filledTime=filledTime # the time when this order is filled.
        self.stop_reached=stop_reached
        self.limit_reached=limit_reached
        self.commission=commission
        self.remaining=remaining
        self.status=status
        self.contract=contract
        self.order=order
        self.orderstate=orderstate
        self.avgFillPrice=avgFillPrice
        
    def __str__(self):
        if self.avgFillPrice>=0.01:
            tp=self.order.action+' '\
                    +self.order.orderType+' '\
                    +str(self.order.totalQuantity)+' shares of '+str(from_contract_to_security(self.contract))+' at '+str(self.avgFillPrice)
        else:
            if self.stop<1e10 and self.limit>1e10:
                tp=self.order.action+' '\
                        +self.order.orderType+' '\
                        +str(self.order.totalQuantity)+' shares of '+str(from_contract_to_security(self.contract))+' at stop price='+str(self.stop)
            elif self.stop>1e10 and self.limit<1e10:
                tp=self.order.action+' '\
                        +self.order.orderType+' '\
                        +str(self.order.totalQuantity)+' shares of '+str(from_contract_to_security(self.contract))+' at limit price='+str(self.limit)
            elif self.stop<1e10 and self.limit<1e10:
                tp=self.order.action+' '\
                        +self.order.orderType+' '\
                        +str(self.order.totalQuantity)+' shares of '+str(from_contract_to_security(self.contract))+' at limit price='+str(self.limit)+' at stop price='+str(self.stop)
            else:
                tp=self.order.action+' '\
                        +self.order.orderType+' '\
                        +str(self.order.totalQuantity)+' shares of '+str(from_contract_to_security(self.contract))+' at unknown price'
        return tp


class ReqHistClass(object):
    def __init__(self,
                    security,
                    barSize,
                    goBack,
                    endTime,
                    whatToShow=None,
                    useRTH=1,
                    formatDate=2,
                    showTimeZone=None):
        self.security=security
        self.barSize=barSize
        '''
        1 sec, 5 secs,15 secs,30 secs,1 min,2 mins,3 mins,5 mins,15 mins,30 mins,1 hour,1 day
        '''        
        self.goBack=goBack
        self.endTime=endTime
        self.whatToShow=whatToShow
        '''
        TRADES,MIDPOINT,BID,ASK,BID_ASK,HISTORICAL_VOLATILITY,OPTION_IMPLIED_VOLATILITY
        '''
        self.useRTH=useRTH
        self.formatDate=formatDate
        self.showTimeZone=showTimeZone
        
        '''
        all request datetime will be switched to UTC then submit to IB
        '''

        self.endTime=self.endTime.astimezone(tz=pytz.utc)
        self.endTime = dt.datetime.strftime(self.endTime,"%Y%m%d %H:%M:%S %Z") #datatime -> string
        if self.whatToShow==None:
            if security.secType in ['STK','FUT', 'IND']:
                self.whatToShow='TRADES'
            elif security.secType in ['CASH', 'OPT', 'CFD']:
                self.whatToShow='ASK'
            else:
                print (__name__+'::ReqHistClass::__init__: EXIT, cannot handle\
                security.secType='+self.security.secType)
                exit()                               
        
#    def __str__(self):
#        return str(self.security)+' barSize='+str(self.barSize)\
#        +' goBack='+str(self.goBack)\
#        +' endTime='+str(dt.datetime.strptime(self.endTime,"%Y%m%d %H:%M:%S %Z").astimezone(self.showTimeZone))+' whatToShow='+str(self.whatToShow)\
#        +' useRTH='+str(self.useRTH)+' formatData='+str(self.formatDate)
    def __str__(self):
        return str(self.security)+' barSize='+str(self.barSize)\
        +' goBack='+str(self.goBack)\
        +' endTime='+str(self.endTime)+' whatToShow='+str(self.whatToShow)\
        +' useRTH='+str(self.useRTH)+' formatData='+str(self.formatDate)


class RequestDataClass(object):
    def __init__(self,
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
                  reqOptionGreeks=None):
        pass
        
        
class EndCheckListClass(object):
    def __init__(self,
                 status=None,
                 reqId=None,
                 input_parameters=None,
                 return_result=None,
                 waiver=False,
                 reqType=None,
                 security=None):
        self.status=status
        self.reqId=reqId
        self.input_parameters=input_parameters
        self.return_result=return_result
        self.waiver=waiver
        self.reqType=reqType
        self.security=security
        
    def __str__(self):
        if self.security!=None:
            output=self.reqType+' reqId='+str(self.reqId)+' '\
                     +str(self.security)+' status='+self.status\
                     +' waiver=' + str(self.waiver)
        else:
            output=self.reqType+' reqId='+str(self.reqId) +' '+self.status           
        return output

class MachineStateClass(FiniteStateClass):
    def __init__(self):
        self.SLEEP = 'SLEEP'
        self.RUN = 'RUN'
        self.INIT ='INIT'

class TimeBasedRules(object):
    def __init__(self,onNthMonthDay='any',
                 onNthWeekDay='any',
                 onHour='any',
                 onMinute='any', func=None):
        self.onNthMonthDay=onNthMonthDay
        self.onNthWeekDay=onNthWeekDay #Monday=0, Friday=4
        self.onHour=onHour
        self.onMinute=onMinute
        self.func=func
    def __str__(self):
        return str(self.onNthMonthDay)+' '+str(self.onNthWeekDay)\
        +' '+str(self.onHour)+' '+str(self.onMinute)+' '+str(self.func)
   
class calendars(object):
    US_EQUITIES=(9,30,16,0)
    US_FUTURES=(6,30,17,0)
    
class time_rules(object):       
    class market_open(object):
        def __init__(self, hours=0, minutes=1):
            self.hour=hours
            self.minute=minutes
            self.version='market_open'
            
    class market_close(object):
        def __init__(self, hours=0, minutes=1):
            self.hour=hours
            self.minute=minutes
            self.version='market_close'
    class spot_time(object):
        def __init__(self, hours=0, minutes=0):
            self.hour=hours
            self.minute=minutes
            self.version='spot_time'
            
class date_rules(object):
    class every_day(object):
        def __init__(self):
            self.version='every_day'
    class week_start(object):
        def __init__(self, days_offset=0):
            self.weekDay=days_offset
            self.version='week_start'
    class week_end(object):
        def __init__(self, days_offset=0):
            self.weekDay=days_offset
            self.version='week_end'
    class month_start(object):
        def __init__(self, days_offset=0):
            self.monthDay=days_offset
            self.version='month_start'
    class month_end(object):
        def __init__(self, days_offset=0):
            self.monthDay=days_offset
            self.version='month_end'
                       
if __name__ == '__main__':
    #a=create_order('BUY',1000,TrailStopLimitOrder(stop_price=1.23, trailing_percent=0.01, limit_offset=0.001))
    #a=create_order('BUY',1000, MarketOrder())    
    #a=TrailStopLimitOrder(stop_price=1.23, trailing_percent=0.01, limit_offset=0.001)
    #a=symbol('OPT,AAPL,USD,20150702,133,P,100')
    #a=symbol('STK,GLD,USD')    
    #print (a.primaryExchange)
    #print (a.__dict__)
    #a=MarketOrder()
    #print (a.exchange)

    ########
    '''
    c=ContextClass(('aaa','bbb'))
    print (c.portfolio['aaa'].positions)
    c.portfolio['aaa'].positions['aa']=1
    print (c.portfolio['aaa'].positions)
    print (c.portfolio['bbb'].positions)
    '''    
    ########
    #a=LimitOrder(2355.0)
    #print (a.__dict__)
    
    #######
    print (search_security_in_file('STK', 'XIV', 'exchange'))