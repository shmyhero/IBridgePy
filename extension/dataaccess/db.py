import traceback

import mysql.connector

from extension.common.common import PathMgr, ConfigMgr
from extension.common.utils import Logger


class BaseDAO(object):

    def __init__(self):
        self.logger = Logger(__name__, PathMgr.get_log_path())

    @staticmethod
    def get_connection():
        db_config = ConfigMgr.get_db_config()
        return mysql.connector.connect(host=db_config['host'], user=db_config['user'], password=db_config['password'], database=db_config['database'])

    def select(self, query, cursor=None):
        #self.logger.info('query:%s' % query)
        conn = None
        if cursor is None:
            conn = BaseDAO.get_connection()
            cursor = conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except Exception as e:
            error_message = "Query:{}, error message: {}, Stack Trace: {}".format(query, str(e), traceback.format_exc())
            self.logger.exception(error_message)
        finally:
            if conn:
                conn.close()


class YahooEquityDAO(BaseDAO):

    def __init__(self):
        BaseDAO.__init__(self)

    def get_equity_price_by_date(self, symbol, date_str, price_field = 'closePrice', cursor=None):
        """
        :param symbol:
        :param date_str: the format is 'YYYY-mm-dd'
        :param price_field:
        :return: price
        """
        query_template = """select {} from yahoo_equity where symbol = '{}' and tradeDate <= str_to_date('{}', '%Y-%m-%d') order by tradeDate desc limit 1"""
        query = query_template.format(price_field, symbol, date_str)
        rows = self.select(query, cursor)
        if rows is None or len(rows) < 1:
            return None
        else:
            return rows[0][0]

    def get_all_equity_price_by_symbol(self, symbol, from_date_str='1993-01-01', price_field = 'adjClosePrice'):
        query_template = """select tradeDate, {} from yahoo_equity where symbol = '{}' and tradeDate >= str_to_date('{}', '%Y-%m-%d') order by tradeDate"""
        query = query_template.format(price_field, symbol, from_date_str)
        rows = self.select(query)
        return rows

