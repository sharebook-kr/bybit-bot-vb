from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from pybit import HTTP
import datetime
import time
import pandas as pd
import numpy as np
import sys


class BackTest(QThread):
    params = pyqtSignal(list)
    message = pyqtSignal(str)

    def __init__(self, symbol, main=None):
        super().__init__()
        self.symbol = symbol 
        self.main = main
        self.df = None
        self.session = HTTP(
            endpoint="https://api.bybit.com",
            spot=False
        )

    def fetch_days(self):
        now = datetime.datetime.now()
        today = datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=0,
            minute=0,
            second=0
        )

        delta = datetime.timedelta(days=-60)
        dt = today + delta 
        from_time = time.mktime(dt.timetuple())

        resp = self.session.query_kline(
            symbol=self.symbol,
            interval="D",
            limit=60+1,         # today
            from_time=from_time
        )

        result = resp['result']
        df = pd.DataFrame(result)
        ts = pd.to_datetime(df['open_time'], unit='s')
        df.set_index(ts, inplace=True)
        return df[['open', 'high', 'low', 'close']]

    @staticmethod
    def backtest(df, window, k, direction):
        df['ma'] = df['close'].rolling(window=window).mean().shift(1)
        df['range'] = (df['high'] - df['low']) * k

        if direction == 1:
            df['target'] = df['open'] + df['range'].shift(1)
        else: 
            df['target'] = df['open'] - df['range'].shift(1)

        # 상승장/하락장 
        df['status'] = df['open'] > df['ma']

        if direction == 1:
            df['수익률'] = np.where((df['high'] > df['target']) & (df['status'] == 1), df['close'] / df['target'], 1)
        else: 
            df['수익률'] = np.where((df['low'] < df['target']) & (df['status'] == 0), df['target'] / df['close'], 1)

        df['누적수익률'] = df['수익률'].cumprod()
        return df

    def find_optimal(self, df, direction):
        best_return = 0
        best_window = 0
        best_k = 0

        for window in range(5, 21):
            for k in np.arange(0.3, 0.7, 0.01):
                df2 = self.backtest(df, window, k, direction)
                cur_return = df2['누적수익률'][-2]

                if cur_return > best_return:
                    best_return = cur_return
                    best_window = window 
                    best_k = k

        #print(best_window, best_k, best_return)
        return (best_window, best_k)

    def run(self):
        df = self.fetch_days()

        up_window, up_k = self.find_optimal(df.copy(), 1)
        up_df = self.backtest(df.copy(), up_window, up_k, 1)
        acc_return = up_df["누적수익률"][-2]
        message = f"{self.symbol} 상승장 누적 수익률: {acc_return:.2f}"
        self.message.emit(message);

        down_window, down_k = self.find_optimal(df.copy(), 0)
        down_df = self.backtest(df.copy(), down_window, down_k, 0)
        acc_return = down_df["누적수익률"][-2]
        message = f"{self.symbol} 하락장 누적 수익률: {acc_return:.2f}"
        self.message.emit(message);

        self.params.emit([
            self.symbol, 
            up_df.iloc[-1]['target'], 
            up_window, 
            up_k, 
            down_df.iloc[-1]['target'], 
            down_window, 
            down_k
        ])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    #coin = BackTest("BTCUSDT")
    #coin = BackTest("ETHUSDT")
    coin = BackTest("XRPUSDT")
    coin.start()
    app.exec_()