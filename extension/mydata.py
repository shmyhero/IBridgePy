import datetime
from abc import ABCMeta, abstractmethod

import pandas as pd

from dataaccess.db import YahooEquityDAO
from tradetime import TradeTime


class AbstractDataProvider(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_symbol_mapping(self):
        return {}

    def get_symbol(self, symbol):
        mapping_dic = self.get_symbol_mapping()
        if symbol in mapping_dic.keys():
            return mapping_dic[symbol]
        else:
            return symbol

    @abstractmethod
    def history(self, symbol, field, window):
        return None


class DBProvider(AbstractDataProvider):

    def __init__(self):
        pass

    def get_symbol_mapping(self):
        return {'SPX':'^GSPC', 'INDU':'^DJI', 'VIX':'^VIX', 'VXV':'^VXV', 'VVIX': '^VVIX', 'RUT':'^RUT', 'NDX': '^NDX'}

    def history(self, symbol, field, window):
        fields_dic = {'open': 'openPrice', 'close': 'adjclosePrice', 'high': 'highPrice', 'low': 'lowPrice',
                      'price': 'adjclosePrice'}
        fields = fields_dic.keys()
        if field.lower() not in field:
            raise Exception('the field should be in %s...'%fields)
        price_field = fields_dic[field]
        yahoo_symbol = self.get_symbol(symbol)
        from_date = TradeTime.get_latest_trade_date() - datetime.timedelta(window * 2)
        rows = YahooEquityDAO().get_all_equity_price_by_symbol(yahoo_symbol, from_date.strftime('%Y-%m-%d'), price_field)
        return rows[-window:]

class MyData(object):

    @staticmethod
    def get_data_provider():
        return DBProvider()

    @staticmethod
    def history(assets, field = 'price', window = 30 ):
        """
        get the history data
        :param assets: symbol likes SPX, SPY, VIX, QQQ, etc, or iterable asset
        :param field: support open, close, high, low, price, the price = close
        :param window: the count of records.
        :return:
        """
        provider = MyData.get_data_provider()
        if hasattr(assets, '__iter__'):
            results = None
            columns = ['date']
            for symbol in assets:
                columns.append(symbol)
                rows = provider.history(symbol, field, window)
                if results is None:
                    results = map(list, rows)
                else:
                    map(lambda x,y: x.append(y[1]), results, rows)
            df = pd.DataFrame(results)
            df.columns = columns
            return df
        else:
            symbol = str(assets)
            rows = provider.history(symbol, field, window)
            df = pd.DataFrame(rows)
            df.columns = ['date', 'price']
            return df

if __name__ == '__main__':
    #print MyData.history('QQQ', field = 'close', window = 100)
    #print MyData.history('SPX')
    print MyData.history(['SPY', 'VIX'], window=50)
    #print map(lambda x : MyData.history(x), ['VIX', 'NDX'])