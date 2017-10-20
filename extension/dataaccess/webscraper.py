from common.utils import HttpHelper
from abc import ABCMeta, abstractmethod

class WebScraper(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_current_data(self):
        pass


class YahooScraper(WebScraper):

    def get_current_data(symbols):
        url_template = 'http://finance.yahoo.com/d/quotes.csv?s={}&f=ophgvd1'
        url = url_template.format(','.join(symbols))
        print url
        content = HttpHelper.http_get(url)
        items = content.split('\n')
        values = map(lambda x: x.split(','), items)
        #values = map(lambda x : [float(x[0]], [float(x[1])]))
        return values


class BarChartScraper(WebScraper):

    def get_current_data(symbols):
        url_template = "http://marketdata.websol.barchart.com/getQuote.json?apikey=7aa9a38e561042d48e32f3b469b730d8&symbols={}"
        url = url_template.format(','.join(symbols))
        print url

if __name__ == '__main__':
    print YahooScraper.get_current_data(['ES=F', 'NQ=F', '^GSPC', '^DJI'])
