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

from IBridgePy.quantopian import Security, PositionClass, \
create_contract, MarketOrder, OrderClass, same_security, \
from_contract_to_security,search_security_in_Qdata
import datetime as dt
import time
from IBridgePy.TraderBase import Trader
import os
from IBridgePy import IBCpp
from sys import exit
import pandas as pd
import numpy as np

class Trader(Trader):
    ################# IB callback functions
    def updateAccountValue(self, key, value, currency, accountCode):
        """
        IB callback function
        update account values such as cash, PNL, etc
        """
        self.log.notset(__name__+'::updateAccountValue: key='+key \
                +' value='+str(value)\
                +' currency=' + currency\
                +' accountCode=' + accountCode)

        if self.validateAccountCode(accountCode):
            if key == 'AvailableFunds':
                self.PORTFOLIO.cash=float(value)
                #print (__name__+'::updateAccountValue: cash=',self.PORTFOLIO.cash)
            elif key == 'UnrealizedPnL':
                self.PORTFOLIO.pnl=float(value)
            elif key == 'NetLiquidation':
                self.PORTFOLIO.portfolio_value=float(value)
                #print (__name__+'::updateAccountValue: portfolio=',self.PORTFOLIO.portfolio_value)
            elif key == 'GrossPositionValue':
                self.PORTFOLIO.positions_value=float(value)
                #print (__name__+'::updateAccountValue: positions=',self.PORTFOLIO.positions_value)
            else:
                pass

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountCode):
        self.log.notset(__name__+'::updatePortfolio')
           
    def accountDownloadEnd(self, accountCode):
        '''
        IB callback function
        '''
        self.log.debug(__name__ + '::accountDownloadEnd: ' + str(accountCode))
        if self.validateAccountCode(accountCode):
            ct=self.search_in_end_check_list(reqType='accountDownload', allowToFail=True)
            if ct!=None:
                self.end_check_list[ct].status='Done'
                
    def accountSummary(self, reqId, accountCode, tag, value, currency):
        self.log.notset(__name__ + '::accountSummary:' + str(reqId) + str(accountCode) + str(tag) + 
        str(value) + str(currency))
        if self.validateAccountCode(accountCode):
            if tag=='TotalCashValue':
                self.PORTFOLIO.cash=float(value)
                self.log.debug(__name__+'::accountSummary: cash change =%s' %(str(self.PORTFOLIO.cash),))
            elif tag=='GrossPositionValue':
                self.PORTFOLIO.positions_value=float(value)
            elif tag=='NetLiquidation':
                self.PORTFOLIO.portfolio_value=float(value)
       
    def accountSummaryEnd(self, reqId):
        self.log.debug(__name__+'::accountSummaryEnd: '+str(reqId))
        ct=self.search_in_end_check_list(reqType='reqAccountSummary', reqId=reqId)
        self.end_check_list[ct].status='Done'
        
    def position(self, accountCode, contract, position, price):
        """
        call back function of IB C++ API which updates the position of a contract
        of a account
        """
        self.log.debug(__name__+'::position: '+accountCode
            +' '+self._print_contract(contract) +','+ str(position) + ', ' + str(price))     
        if self.validateAccountCode(accountCode):
            security=from_contract_to_security(contract)
            adj_security=search_security_in_Qdata(self.qData, security, self.logLevel)
            securityFound=self.search_security_in_positions(adj_security, accountCode)
            self.PORTFOLIO.positions[securityFound].amount=position
            self.PORTFOLIO.positions[securityFound].cost_basis=price       
            self.PORTFOLIO.positions[securityFound].accountCode=accountCode

    def orderStatus(self,orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
        """
        call back function of IB C++ API which update status or certain order
        indicated by orderId
        Same orderId may be called back muliple times with status of 'Filled'
        """
        self.log.debug(__name__+'::orderStatus: ' + str(orderId) + ", " + str(status) + ", "
        + str(filled) + ", " + str(remaining) + ", " + str(avgFillPrice))

        accountCode=self.orderId_to_accountcode(orderId)       
        accountCode=self.validateAccountCode(accountCode)
        self.PORTFOLIO.orderStatusBook[orderId].filled=filled
        self.PORTFOLIO.orderStatusBook[orderId].remaining=remaining
        self.PORTFOLIO.orderStatusBook[orderId].status=status
        self.PORTFOLIO.orderStatusBook[orderId].avgFillPrice=avgFillPrice
        if (self.PORTFOLIO.orderStatusBook[orderId].parentOrderId 
        is not None and status == 'Filled'):
            if (self.PORTFOLIO.orderStatusBook[orderId].stop is not None):
                self.PORTFOLIO.orderStatusBook[
                self.PORTFOLIO.orderStatusBook[orderId].parentOrderId].stop_reached = True
                self.log.info(__name__ + "::orderStatus " + "stop executed: " + 
                self.PORTFOLIO.orderStatusBook[orderId].contract.symbol)
            if (self.PORTFOLIO.orderStatusBook[orderId].limit is not None):
                self.PORTFOLIO.orderStatusBook[
                self.PORTFOLIO.orderStatusBook[orderId].parentOrderId].limit_reached = True
                self.log.info(__name__ + "::orderStatus " + "limit executed: " +
                self.PORTFOLIO.orderStatusBook[orderId].contract.symbol)               

    def openOrder(self, orderId, contract, order, orderstate):
        """
        call back function of IB C++ API which updates the open orders indicated
        by orderId
        """
        self.log.debug(__name__+"::openOrder: " + str(orderId) + ', ' + str(contract.symbol) + 
        '.' + str(contract.currency) + ', ' + str(order.action) + ', ' + 
        str(order.totalQuantity))

        self.validateAccountCode(order.account)
        if orderId in self.PORTFOLIO.orderStatusBook:
            if self.PORTFOLIO.orderStatusBook[orderId].contract!=contract:
                self.PORTFOLIO.orderStatusBook[orderId].contract=contract                        
            if self.PORTFOLIO.orderStatusBook[orderId].order!=order:
                self.PORTFOLIO.orderStatusBook[orderId].order=order                        
            if self.PORTFOLIO.orderStatusBook[orderId].orderstate!=orderstate:
                self.PORTFOLIO.orderStatusBook[orderId].orderstate=orderstate                        
            self.PORTFOLIO.orderStatusBook[orderId].status=orderstate.status            
        else:
            self.PORTFOLIO.orderStatusBook[orderId] = \
                OrderClass(orderId=orderId,
                           created=dt.datetime.now(),
                    stop=(lambda x: x if x<100000 else None)(order.auxPrice),
                    limit=(lambda x: x if x<100000 else None)(order.lmtPrice),
                    amount=order.totalQuantity,
                    commission=(lambda x: x if x<100000 else None)(orderstate.commission),
                    status=orderstate.status,
                    contract=contract,
                    order=order,
                    orderstate=orderstate)

    def execDetails(self, reqId, contract, execution):
        self.log.debug(__name__+'::execDetails: reqId= %i' %(int(reqId),) \
        + str(from_contract_to_security(contract)))
        self.log.debug(__name__+'::execDetails: %s %s %s %s %s %s'\
        %(str(execution.side),str(execution.shares),str(execution.price),\
        str(execution.orderRef), str(execution.orderId), str(execution.clientId)))
        if self.validateAccountCode(execution.acctNumber):
            cashChange=execution.shares*float(execution.price)
            if execution.side=='BOT':           
                self.PORTFOLIO.cash-=cashChange
            elif execution.side=='SLD':
                self.PORTFOLIO.cash+=cashChange
            else:
                self.log.error(__name__+'::execDetails: EXIT, cannot handle execution.side='+execution.side)
                exit()
            self.log.debug(__name__+'::execDetails: cash= %f' %(float(self.PORTFOLIO.cash),))
            if execution.orderRef not in self.PORTFOLIO.performanceTracking:
                self.PORTFOLIO.performanceTracking[execution.orderRef]=\
                pd.DataFrame({'security':'NA',
                          'action':'NA',
                          'quantity':0,
                          'avgFillPrice':0,
                          'virtualStrategyBalance':0},
                          index=[self.get_datetime()])
                
            security=from_contract_to_security(contract)
            action=str(execution.side)
            quantity=float(execution.shares)
            avgFillPrice=float(execution.price)
            virtualStrategyBalance=self.track_performance(execution.orderRef,
                                                          security,
                                                          action,
                                                          quantity,
                                                          avgFillPrice,
                                                          execution.acctNumber)
            #print self.PORTFOLIO.virtualHoldings
            #prev=self.PORTFOLIO.performanceTracking[execution.orderRef].ix[-1, 'virtualStrategyBalance']
            #print prev,virtualStrategyBalance
            if virtualStrategyBalance==None:
                virtualStrategyBalance=np.nan
            newRow=pd.DataFrame({'security':str(security),
                          'action':action,
                          'quantity':quantity,
                          'avgFillPrice':avgFillPrice,
                          'virtualStrategyBalance':virtualStrategyBalance},
                          index=[self.get_datetime()])
            self.PORTFOLIO.performanceTracking[execution.orderRef]=\
            self.PORTFOLIO.performanceTracking[execution.orderRef].append(newRow)
            #print self.PORTFOLIO.performanceTracking[execution.orderRef]
                                
    
    ########## IBridgePy action functions    
    def order(self, security, amount, style=MarketOrder(), orderRef='',
              accountCode='default'):
        self.log.debug(__name__+'::order:'+str(security)+' '+str(amount) )                         

        if amount>0:  
            action='BUY'
        elif amount<0:
            action='SELL'
            amount=-amount
        else:
            self.log.debug(__name__+'::order: No order has been placed')
            return 0
        tmp=self.create_order(action, amount, security, style, orderRef=orderRef)
        if tmp!=None:
            return self.IBridgePyPlaceOrder(tmp, accountCode=accountCode)
        else:
            self.log.error(__name__+ '::order: EXIT wrong serurity instance '+str(security))
            exit()

    def order_target(self, security, amount, style=MarketOrder(),orderRef='',
                     accountCode='default'):
        self.log.notset(__name__ + '::order_target') 
        hold=self.count_positions(security,accountCode=accountCode) 
        if amount!=hold:
            return self.order(security, amount=amount-hold, style=style,
                              orderRef=orderRef, accountCode=accountCode)
        else:
            self.log.debug(__name__+'::order_target: %s No action is needed' %(str(security),))
            return 0

    def order_target_II(self, security, amount, style=MarketOrder(), accountCode='default'):
        self.log.notset(__name__ + '::order_target_II') 
        hold=self.count_positions(security,accountCode=accountCode)  
        if (hold>=0 and amount>0) or (hold<=0 and amount<0):
            orderID=self.order(security, amount=amount-hold, style=style,accountCode=accountCode)
            if self.order_status_monitor(orderID,'Filled'):
                return orderID
        if (hold>0 and amount<0) or (hold<0 and amount>0):
            orderID=self.order_target(security, 0,accountCode=accountCode)
            if self.order_status_monitor(orderID,'Filled'):
                orderID=self.order(security, amount,accountCode=accountCode)
                if self.order_status_monitor(orderID,'Filled'):
                    return orderID
                else:
                    self.log.debug(__name__+'::order_target_II:orderID=%s was not processed as expected. EXIT!!!' %(orderID,))
                    return 0
            else:    
                self.log.debug(__name__+'::order_target_II:orderID=%s was not processed as expected. EXIT!!!' %(orderID,))
                return 0
        if hold==amount:
            self.log.debug(__name__+'::order_target_II: %s No action is needed' %(str(security),))
            return 0
        else:
            self.log.debug(__name__+'::order_target_II: hold='+str(hold) )
            self.log.debug(__name__+'::order_target_II: amount='+str(amount) )
            self.log.debug(__name__+'::order_target_II: Need debug EXIT' )
            exit()            

    def cancel_all_orders(self, accountCode='default'):
        self.log.notset(__name__+'::cancel_all_orders') 
        accountCode=self.validateAccountCode(accountCode)
        for orderId in self.PORTFOLIO.orderStatusBook:
            if self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled','Cancelled', 'Inactive']:
                self.cancel_order(orderId) 

    def display_positions(self, accountCode='default'):
        self.log.notset(__name__+'::display_positions')  
        if not self.displayFlag:
            return
        accountCode=self.validateAccountCode(accountCode)
        if self.hold_any_position(accountCode=accountCode):
            self.log.info( '##    POSITIONS    ##')
            self.log.info( 'Symbol Amount Cost_basis Latest_profit')    

            for ct in self.PORTFOLIO.positions:            
                if self.PORTFOLIO.positions[ct].amount!=0:
                    a=self.qData.data[search_security_in_Qdata(self.qData, ct, self.logLevel)].last_traded
                    b=self.PORTFOLIO.positions[ct].cost_basis
                    c=self.PORTFOLIO.positions[ct].amount
                    if a!=None and a!=-1:
                        self.log.info( str(ct)+' '+str(c)+' ' +str(b)+' '+str((a-b)*c )) 
                    else:
                        self.log.info( str(ct)+' '+str(c)+' ' +str(b)+' NA') 
                        
            self.log.info( '##    END    ##')               
        else:
            self.log.info( '##    NO ANY POSITION    ##')

    def display_orderStatusBook(self, accountCode='default'): 
        self.log.notset(__name__+'::display_orderStatusBook')          
        if not self.displayFlag:
            return

        #show orderStatusBook
        accountCode=self.validateAccountCode(accountCode)
        if len(self.PORTFOLIO.orderStatusBook) >=1:
            self.log.info( '##    Order Status    ##')               
            for orderId in self.PORTFOLIO.orderStatusBook:
                self.log.info( 'reqId='+str(orderId)+' '\
                        +' '+self.PORTFOLIO.orderStatusBook[orderId].status\
                        +' '+str(self.PORTFOLIO.orderStatusBook[orderId]))
            self.log.info( '##    END    ##')               
        else:
            self.log.info( '##    NO any order    ##')
            
    def display_account_info(self, accountCode='default'):
        """
        display account info such as position values in format ways
        """
        self.log.notset(__name__ + '::display_acount_info')
        if not self.displayFlag:
            return

        accountCode=self.validateAccountCode(accountCode)
        self.log.info('##    ACCOUNT Balance  %s  ##' %(accountCode,))
        self.log.info('CASH=' + str(self.PORTFOLIO.cash))
        #self.log.info('pnl=' + str(self.PORTFOLIO.pnl))
        self.log.info('portfolio_value=' + str(self.PORTFOLIO.portfolio_value))
        self.log.info('positions_value=' + str(self.PORTFOLIO.positions_value))
        #self.log.info('returns=' + str(self.PORTFOLIO.returns))
        #self.log.info('starting_cash=' + str(self.PORTFOLIO.starting_cash))
        #self.log.info('start_date=' + str(self.PORTFOLIO.start_date))

    def display_all(self, accountCode='default'):
        if not self.displayFlag:
            return
        accountCode=self.validateAccountCode(accountCode)
        self.display_account_info(accountCode)
        self.display_positions(accountCode)
        self.display_orderStatusBook(accountCode)

    def order_status_monitor(self, orderId, target_status, waitingTimeInSeconds=30 ):
        self.log.notset(__name__+'::order_status_monitor')
        if orderId==-1:
            self.log.error(__name__+'::order_status_monitor: EXIT, orderId=-1' )
            exit()
        elif orderId==0:
            return True
        else:
            timer=dt.datetime.now()
            exit_flag=True
            while(exit_flag):
                time.sleep(0.1)
                self.processMessages()
                accountCode=self.orderId_to_accountcode(orderId)
                accountCode=self.validateAccountCode(accountCode)
                if (dt.datetime.now()-timer).total_seconds()<=waitingTimeInSeconds:
                    if self.PORTFOLIO.orderStatusBook[orderId].status=='Filled':
                        self.log.info(__name__+'::order_status_monitor: Filled '+str(self.PORTFOLIO.orderStatusBook[orderId]))                     
                        return True
                elif self.PORTFOLIO.orderStatusBook[orderId].status==target_status:
                        return True    
                elif self.PORTFOLIO.orderStatusBook[orderId].status=='Inactive':
                        self.log.error(__name__+'::order_status_monitor: EXIT, status=Inactive!!!, orderId=%i, %s' %(orderId, str(from_contract_to_security(self.PORTFOLIO.orderStatusBook[orderId].contract))    ))
                        exit()                       
                else:
                    self.log.error(__name__+'::order_status_monitor: EXIT, waiting time is too long, >%i, orderId=%i, %s, %s' %(waitingTimeInSeconds,orderId,str(from_contract_to_security(self.PORTFOLIO.orderStatusBook[orderId].contract)),self.PORTFOLIO.orderStatusBook[orderId].status))
                    exit()
                    

    def close_all_positions(self, orderStatusMonitor=True, accountCode='default'):
        self.log.debug(__name__+'::close_all_positions:')
        accountCode=self.validateAccountCode(accountCode)
        tp=self.PORTFOLIO.positions.keys()
        orderIdList=[]
        for security in tp:
            orderId=self.order_target(security, 0,accountCode=accountCode)
            orderIdList.append(orderId)
        if orderStatusMonitor:
            for orderId in orderIdList:
                self.order_status_monitor(orderId, 'Filled')

    def close_all_positions_except(self, a_security, accountCode='default'):
        self.log.debug(__name__+'::close_all_positions_except:'+str(a_security))
        accountCode=self.validateAccountCode(accountCode)
        tp=self.PORTFOLIO.positions.keys()
        orderIdList=[]
        for security in tp:
            if same_security(a_security, security):
                pass
            else:
                orderId=self.order_target(security, 0,accountCode=accountCode)
                orderIdList.append(orderId)
        for orderId in orderIdList:
            self.order_status_monitor(orderId, 'Filled')                

    def show_account_info(self, infoName, accountCode='default' ):
        #self.request_data(accountDownload=self.accountCode)
        accountCode=self.validateAccountCode(accountCode)
        if hasattr(self.PORTFOLIO, infoName):
            tp=getattr(self.PORTFOLIO, infoName)
            return tp
        else:
            self.log.error(__name__+'::show_account_info: ERROR, context.portfolio of accountCode=%s does not have attr=%s' %(self.accountCode, infoName))
            exit()

    def count_open_orders(self, security='All', accountCode='default'):
        self.log.debug(__name__+'::count_open_orders') 
        accountCode=self.validateAccountCode(accountCode)
        count=0
        for orderId in self.PORTFOLIO.orderStatusBook:
            if  self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled','Cancelled','Inactive']: 
                if security=='All':          
                    count += self.PORTFOLIO.orderStatusBook[orderId].amount                     
                else:
                    tp=self.PORTFOLIO.orderStatusBook[orderId].contract
                    tp=from_contract_to_security(tp)
                    if same_security(tp,security):
                        count += self.PORTFOLIO.orderStatusBook[orderId].amount                     
        return count

    def count_positions(self, a_security, accountCode='default'):
        self.log.debug(__name__+'::count_positions') 
        accountCode=self.validateAccountCode(accountCode)
        for sec in self.PORTFOLIO.positions:
            if same_security(sec,a_security):
                return self.PORTFOLIO.positions[sec].amount
        return 0

    def hold_any_position(self, accountCode='default'):
        self.log.notset(__name__+'::hold_any_position')
        accountCode=self.validateAccountCode(accountCode)
        for ct in self.PORTFOLIO.positions:
            if self.PORTFOLIO.positions[ct].amount!=0:
                return True
        return False        
             
    def calculate_profit(self, a_security, accountCode='default'):
        self.log.notset(__name__+'::calculate_profit:'+str(a_security))
        accountCode=self.validateAccountCode(accountCode)
        tp=search_security_in_Qdata(self.qData, a_security, self.logLevel)
        a=self.show_real_time_price(tp, 'ask_price')
        b=self.PORTFOLIO.positions[tp].cost_basis
        c=self.PORTFOLIO.positions[tp].amount
        if a!=None and a!=-1:
            return (a-b)*c 
        else:
            return None
        
    def get_order(self, order, accountCode='default'):
        accountCode=self.validateAccountCode(accountCode)
        if type(order)==str:
            if order in self.PORTFOLIO.orderStatusBook:
                return self.PORTFOLIO.orderStatusBook[order]
            else:
                self.log.error(__name__+'::get_order: EXIT, invalid orderId=%s' %(str(order), ))
        elif type(order)==OrderClass:
            if order.orderId in self.PORTFOLIO.orderStatusBook:
                return self.PORTFOLIO.orderStatusBook[order]
            else:
                self.log.error(__name__+'::get_order: EXIT, invalid orderId=%s' %(str(order), ))           

    def get_open_orders(self, sid=None, accountCode='default'):
        self.log.debug(__name__+'::get_open_orders') 
        accountCode=self.validateAccountCode(accountCode)
        if sid==None:
            ans={}
            for orderId in self.PORTFOLIO.orderStatusBook:
                if  self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled','Cancelled','Inactive']:
                    tp=self.PORTFOLIO.orderStatusBook[orderId].contract
                    security=from_contract_to_security(tp)
                    security=search_security_in_Qdata(self.qData, security, self.logLevel)             
                    if security not in ans:
                        ans[security]=[self.PORTFOLIO.orderStatusBook[orderId]]
                    else:
                        ans[security].append(self.PORTFOLIO.orderStatusBook[orderId])
            return ans  
        else:
            ans=[]
            for orderId in self.PORTFOLIO.orderStatusBook:
                if  self.PORTFOLIO.orderStatusBook[orderId].status not in ['Filled','Cancelled','Inactive']:
                    tp=self.PORTFOLIO.orderStatusBook[orderId].contract
                    security=from_contract_to_security(tp)
                    security=search_security_in_Qdata(self.qData, security, self.logLevel)             
                    if same_security(sid, security):
                        ans.append(self.PORTFOLIO.orderStatusBook[orderId])
            return ans

    ######### IBridgePy supportive functions       
    def _build_security_in_positions(self, a_security, accountCode='default'):
        self.log.notset(__name__+'::_build_security_in_positions')  
        accountCode=self.validateAccountCode(accountCode)
        if self.PORTFOLIO.positions=={}:
            self.PORTFOLIO.positions[a_security]=PositionClass()
            self.log.notset(__name__+'::_build_security_in_positions: Empty,\
            add a new position '+str(a_security))
            return
        else:
            # if found, then do nothing
            # else: add it into positions.
            for sec in self.PORTFOLIO.positions:
                if same_security(sec, a_security):
                    return
            self.PORTFOLIO.positions[a_security]=PositionClass()
            self.log.notset(__name__+'::_build_security_in_positions: Empty,\
            add a new position '+str(a_security))
            return

    def build_security_in_positions(self, a_security, accountCode='default'):
        if accountCode=='default':
            self._build_security_in_positions(a_security, accountCode)
        else:
            if type(self.accountCode)==str:
                self._build_security_in_positions(a_security, self.accountCode)
            else:
                for accountCode in self.accountCode:
                    self._build_security_in_positions(a_security, accountCode)
                                   
    def search_security_in_positions(self, a_security, accountCode='default'):
        self.log.notset(__name__+'::search_security_in_positions')  
        # if positions is empty, add new security, then return
        accountCode=self.validateAccountCode(accountCode)
        if self.PORTFOLIO.positions=={}:
            self.PORTFOLIO.positions[a_security]=PositionClass()
            self.log.notset(__name__+'::search_security_in_positions: Empty, add a new position '+str(a_security))
            return a_security
        # search security in positions, if found only one, return,
        foundFlag=0
        found={}
        for ct in self.PORTFOLIO.positions:
            if same_security(ct, a_security):
                foundFlag=foundFlag+1
                found[foundFlag]=ct
        if foundFlag==1:
            return found[1]
        elif foundFlag==0:   
            # a_security is not in positions,  add it in it               
            self.PORTFOLIO.positions[a_security]=PositionClass()
            self.log.notset(__name__+'::search_security_in_positions: cannot find one, add a new position '+str(a_security))
            return a_security
        else:
            self.log.error(__name__+'::search_security_in_positions: EXIT, found too many securities')
            for ct in found:
                self.log.error(str(found[ct]))
            exit()  

 
    def check_if_any_unfilled_orders(self, verbose=False, accountCode='default'):
        self.log.notset(__name__+'::check_if_any_unfilled_orders')      
        accountCode=self.validateAccountCode(accountCode)
        flag=False
        for orderId in self.PORTFOLIO.orderStatusBook:
            if  self.PORTFOLIO.orderStatusBook[orderId].status!='Filled': 
                flag=True
        if flag==True:
            if verbose==True:
                self.log.info(__name__+'::check_if_any_unfilled_orders: unfilled orderst are:')
                self.display_orderStatusBook(accountCode)
        return flag        
 
        
    def IBridgePyPlaceOrder(self, an_order, accountCode='default'):
        self.log.debug(__name__+'::IBridgePyPlaceOrder')
        adj_accountCode=self.validateAccountCode(accountCode)
        if adj_accountCode==None:
            self.log.error(__name__+'::IBridgePyPlaceOrder: EXIT, unexpected accountCode=%s' %(accountCode,))
            exit()
        an_order.order.account=adj_accountCode
        an_order.orderId=self.nextId
        an_order.created=self.get_datetime()
        an_order.stop=an_order.order.auxPrice
        an_order.limit=an_order.order.lmtPrice
        an_order.amount=an_order.order.totalQuantity
        an_order.status='PreSubmitted'
        self.PORTFOLIO.orderStatusBook[self.nextId] = an_order
        self.log.debug(__name__+'::IBridgePyPlaceOrder: accountCode=%s' %(an_order.order.account,))
        self.log.debug(__name__+'::IBridgePyPlaceOrder: REQUEST orderId=%s %s' %(self.nextId, str(self.PORTFOLIO.orderStatusBook[self.nextId]) ) )
        self.log.debug(__name__+'::IBridgePyPlaceOrder: %s'%(str(self.get_datetime()),) )
        tmp=self.nextId #in the test_run mode, self.nextId may change after self.placeOrder, so, record it at first place
        self.nextId=self.nextId+1
        self.placeOrder(tmp, an_order.contract, an_order.order)
        return tmp
        
    def get_performance(self, orderRef, accountCode='default'):
        self.log.debug(__name__+'::get_performance: %s %s' %(orderRef,accountCode))
        self.validateAccountCode(accountCode)
        if orderRef in self.PORTFOLIO.performanceTracking:
            a= self.PORTFOLIO.performanceTracking[orderRef]
            c=a[a['virtualStrategyBalance']<=0x7FFFFFFF]
            return c['virtualStrategyBalance']       
        else:
            return []

    def track_performance(self, orderRef, security, action, quantity, avgFillPrice, accountCode='default'):
        security=str(security)        
        self.log.debug(__name__+'::track_performance: %s %s' %(orderRef,accountCode))

        self.validateAccountCode(accountCode)
        if orderRef not in self.PORTFOLIO.virtualHoldings:
            self.PORTFOLIO.virtualHoldings[orderRef]={}
        if security not in self.PORTFOLIO.virtualHoldings[orderRef]:
            self.PORTFOLIO.virtualHoldings[orderRef][security]={'action':action, 
            'quantity':quantity, 'avgFillPrice':avgFillPrice}
            return None

        q=self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity']
        p=self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFillPrice']
        if action==self.PORTFOLIO.virtualHoldings[orderRef][security]['action']:
            self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFilePrice']=\
            (q*p+quantity*avgFillPrice)/(q+quantity)
            self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity']+=quantity
            return None
        else:
            if q>quantity:
                self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity']-=quantity
                if action=='SLD':
                    return (avgFillPrice-p)*quantity
                else:
                    return -(avgFillPrice-p)*quantity
            elif q<quantity:
                self.PORTFOLIO.virtualHoldings[orderRef][security]['action']=action
                self.PORTFOLIO.virtualHoldings[orderRef][security]['quantity']=quantity-q
                self.PORTFOLIO.virtualHoldings[orderRef][security]['avgFillPrice']=avgFillPrice
                if action=='SLD':
                    return (avgFillPrice-p)*q
                else:
                    return -(avgFillPrice-p)*q
            else:
                if action=='SLD':
                    tmp= (avgFillPrice-p)*q
                else:
                    tmp= -(avgFillPrice-p)*q
                del self.PORTFOLIO.virtualHoldings[orderRef][security]
                return tmp
                    
                                
                
        
    ############# special functiont
    def validateAccountCode(self, accountCode):
        self.log.notset(__name__+'::validateAccountCode: %s' %(accountCode,))
        if accountCode=='default':
            accountCode=self.accountCode
        if accountCode == self.accountCode:
            self.PORTFOLIO=self.context.portfolio
            return accountCode
        else:
            if 'DUC' in accountCode:
                pass
            else:
                self.log.error(__name__ + '::validateAccountCode: EXIT, unexpect accountN=%s' %(accountCode,))
                self.log.error(__name__ + '::validateAccountCode: Input accoutCode '+str(self.accountCode))
                self.log.error('Please contact with IBridgePy@gmail.com about IBridgePy for Multi Account')
                exit()
        
    def orderId_to_accountcode(self, orderId):
        return self.accountCode
    
       
        
            