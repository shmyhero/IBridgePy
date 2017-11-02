import pandas as pd
from dataaccess.history import DBProvider
from dataaccess.symbols import Symbols
from dataaccess.webscraper import YahooScraper, BarChartScraper, MarketWatchScraper


class MyData(object):

    @staticmethod
    def get_historical_data_provider():
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
        provider = MyData.get_historical_data_provider()
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
            df = pd.DataFrame(map(lambda x: x[1:], results), index=map(lambda x: x[0], results), columns=columns[1:])
            return df
        else:
            symbol = str(assets)
            rows = provider.history(symbol, field, window)
            df = pd.DataFrame(map(lambda x: x[1:], rows), index= map(lambda x: x[0], rows), columns = ['price'])
            return df

    @staticmethod
    def get_current_data_provider(symbols):
        return MarketWatchScraper()
        #if len(symbols) == 1:
        #    return MarketWatchScraper()
        #else:
        #    return YahooScraper()
        #for symbol in symbols:
        #    if symbol in Symbols.Indexes:
        #        return YahooScraper()
        #return BarChartScraper()

    @staticmethod
    def current(symbols, fields=['price']):
        if type(symbols) is str:
            symbols = [symbols]
        if type(fields) is str:
            fields = [fields]
        field_dic = {'open':0, 'close':1, 'price':1, 'high':2, 'low':3, 'volume':4, 'contract':5 }
        indexes = map(lambda x: field_dic[x],fields)
        provider = MyData.get_current_data_provider(symbols)
        records = provider.get_current_data(symbols)
        if len(symbols) == 1 and len(fields) == 1:
            return records[0][0]
        elif len(symbols) > 1 and len(fields) == 1:
            values = map(lambda x: x[indexes[0]], records)
            return pd.Series(values, index=symbols)
        elif len(symbols) == 1 and len(fields) >= 1:
            values = map(lambda index: records[0][index], indexes)
            return pd.Series(values, index=fields)
        else:
            rows = map(lambda record: map(lambda index: record[index], indexes), records)
            prefixed_row = map(lambda x,y: [x] + y, symbols, rows )
            df = pd.DataFrame(prefixed_row, columns=['symbol'] + fields)
            return df


if __name__ == '__main__':
    #print MyData.history('QQQ', field = 'close', window = 100)
    #print MyData.history('SPX')
    #print MyData.history(['SPY', 'VIX'], window=252)
    #print MyData.current(['SPY', 'QQQ', 'VIX', 'NDX'], ['price', 'volume'])
    #print MyData.current(['SPY', 'QQQ', 'AAPL'], ['price', 'open', 'high', 'low', 'close', 'volume'])
    print MyData.current(['SPY', 'QQQ', 'AAPL', 'NDX'], ['price', 'open', 'high', 'low', 'close'])
    #print MyData.current(['DJI'], ['price', 'open', 'high', 'low', 'close', 'volume'])
    #print MyData.current(['DJI', 'SPY'], 'price')
    #print MyData.current('SPY', ['open', 'close', 'high', 'low'])
