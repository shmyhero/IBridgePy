# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 15:37:16 2017

@author: IBridgePy@gmail.com
"""
import operator
op={'Equal':operator.eq, 'Greater than':operator.gt, 
    'Greater or equal':operator.ge, 'Less than':operator.lt, 
    'Less or equal':operator.le}

class TradingRules(object):
    def __init__(self, 
                 security,
                 purchaseAmount,
                 orderType,
                 rounding,
                 limitPrice=None,
                 stopPrice=None,
                 indicatorName=None,
                 inputParams=None,
                 indicatorDetails=[]):
        self.security=security
        self.purchaseAmount=purchaseAmount
        self.orderType=orderType
        self.rounding=rounding
        self.limitPrice=limitPrice
        self.stopPrice=stopPrice
        self.indicatorNumber=len(indicatorDetails)
        self.indicatorDetails=indicatorDetails
    def __str__(self):
        tmp=''
        for i,ct in enumerate(self.indicatorDetails):
            tmp+='rule '+str(i)+'::'+str(ct)+' \n'
        ans='security=%s purchaseAmount=%s orderType=%s rounding=%s limitPrice=%s stopPrice=%s indicatorNumber=%s \nindicatorDetails:\n%s'\
        %(str(self.security),str(self.purchaseAmount),str(self.orderType),str(self.rounding),str(self.limitPrice),str(self.stopPrice),str(self.indicatorNumber),str(tmp))
        return ans
    
class IndicatorDetails(object):
    def __init__(self, 
                 priceNameToBeCompared,
                 comparingMethod,
                 inputParams):
        self.priceNameToBeCompared=priceNameToBeCompared
        self.comparingMethod=op[comparingMethod] # 1: equal 2: Greater than 3:Greater or equal 4:Less than 5 less or equal 
        self.inputParams=inputParams
        self.indicatorName=inputParams.name

        
    def __str__(self):
        ans='priceNameToBeCompared=%s comparingMethod=%s indicatorName=%s \ninputParams: %s'\
        %(str(self.priceNameToBeCompared), str(self.comparingMethod), str(self.indicatorName), str(self.inputParams))
        return ans
    
class Indicator(object):
    def __init__(self):
        pass
    class Bollinger(object):
        def __init__(self, k=2, n=14, period='1 day'):
            self.k=k
            self.n=n
            self.period=period
            self.name='Bollinger'
        def __str__(self):
            ans='%s k=%i n=%i period=%s' %(self.name, self.k, self.n, self.period)
            return ans
    class Range(object):
        def __init__(self, n=-2, loc='high', period='1 day'):
            self.n=n
            self.loc=loc
            self.period=period
            self.name='Range'
        def __str__(self):
            ans='%s n=%i loc=%s period=%s' %(self.name, self.n, self.loc, self.period)
            return ans
    
if __name__=='__main__':
    import pandas as pd
    tradingRules=[]
    for i in range(len(f)):
        b1=Indicator.Bollinger(f.iloc[i]['bollingerK'], f.iloc[i]['bollingerN'])
        r1=IndicatorDetails(f.iloc[i]['priceNameToBeCompared'], f.iloc[i]['comparingMethod'], b1)
        t=TradingRules(f.iloc[i]['purchaseAmount'], f.iloc[i]['orderType'], f.iloc[i]['rounding'], indicatorDetails=[r1])
        tradingRules.append(t)
        #print (t)
    print (tradingRules[0].indicatorDetails[0].comparingMethod(3,4))
    
    '''
    b1=Indicator.Bollinger(2, 14)
    b2=Indicator.Bollinger(3, 20)
    r1=IndicatorDetails('ask_price', 3, 'bollinger', b1)
    r2=IndicatorDetails('ask_price', 3, 'bollinger', b2)
    t=TradingRules(100, 'MKT', 0.01, indicatorDetails=[r1,r2])
    print (t)
    '''