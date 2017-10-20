
class Mapping(object):

    YahooSymbolMapping = {'SPX':'^GSPC', 'INDU':'^DJI', 'VIX':'^VIX', 'VXV':'^VXV', 'VVIX': '^VVIX', 'RUT':'^RUT', 'NDX': '^NDX'}

    @staticmethod
    def get_mapped_symbol(symbol, mapping_dic):
        if symbol in mapping_dic.keys():
            return mapping_dic[symbol]
        else:
            return symbol