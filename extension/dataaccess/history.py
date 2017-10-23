from abc import ABCMeta, abstractmethod
from dataaccess.symbols import Symbols
from dataaccess.db import YahooEquityDAO
from tradetime import TradeTime


class AbstractHistoricalDataProvider(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def history(self, symbol, field, window):
        return None


class DBProvider(AbstractHistoricalDataProvider):

    def __init__(self):
        pass

    def history(self, symbol, field, window):
        fields_dic = {'open': 'openPrice', 'close': 'adjclosePrice', 'high': 'highPrice', 'low': 'lowPrice',
                      'price': 'adjclosePrice'}
        fields = fields_dic.keys()
        if field.lower() not in field:
            raise Exception('the field should be in %s...'%fields)
        price_field = fields_dic[field]
        yahoo_symbol = Symbols.get_mapped_symbol(symbol, Symbols.YahooSymbolMapping)
        from_date = TradeTime.get_from_date_by_window(window)
        rows = YahooEquityDAO().get_all_equity_price_by_symbol(yahoo_symbol, from_date.strftime('%Y-%m-%d'), price_field)
        return rows