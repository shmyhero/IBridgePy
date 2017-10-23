
class Symbols(object):

    YahooSymbolMapping = {'SPX':'^GSPC', 'INDU':'^DJI', 'VIX':'^VIX', 'VXV':'^VXV', 'VVIX': '^VVIX', 'RUT':'^RUT', 'NDX': '^NDX'}

    Indexes = ['SPX', 'INDU', 'VIX', 'VXV', 'VVIX', 'RUT', 'NDX']

    @staticmethod
    def get_mapped_symbol(symbol, mapping_dic):
        if symbol in mapping_dic.keys():
            return mapping_dic[symbol]
        else:
            return symbol