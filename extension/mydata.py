import pandas as pd
from dataaccess.history import DBProvider




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
            df = pd.DataFrame(map(lambda x: x[1:], results), index=map(lambda x: x[0], results), columns=columns[1:])
            return df
        else:
            symbol = str(assets)
            rows = provider.history(symbol, field, window)
            df = pd.DataFrame(map(lambda x: x[1:], rows), index= map(lambda x: x[0], rows), columns = ['price'])
            return df

if __name__ == '__main__':
    #print MyData.history('QQQ', field = 'close', window = 100)
    #print MyData.history('SPX')
    print MyData.history(['SPY', 'VIX'], window=252)