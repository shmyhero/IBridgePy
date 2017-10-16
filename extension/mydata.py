import datetime
import pandas as pd
from abc import ABCMeta, abstractmethod
from tradetime import TradeTime
from dataaccess import YahooEquityDAO


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


class YahooDBProvider(AbstractDataProvider):

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
        df = pd.DataFrame(rows[-window:])
        df.columns = ['date', 'price']
        return df


class MyData(object):

    @staticmethod
    def get_data_provider():
        return YahooDBProvider()

    @staticmethod
    def history(symbol, field = 'price', window = 30 ):
        provider = MyData.get_data_provider()
        return provider.history(symbol, field, window)


if __name__ == '__main__':
    #print MyData.history('QQQ', field = 'close', window = 100)
    print MyData.history('SPX')