from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from pybit import HTTP
import time
import sys
import pprint
import datetime


class Trader(QThread):
    def __init__(self, symbol, main=None):
        super().__init__()

        self.symbol = symbol 
        self.main = main

        with open("../../../bybit.key") as f:
            lines = f.readlines()
            api_key = lines[0].strip()
            api_secret = lines[1].strip()

        self.session = HTTP(
            endpoint="https://api.bybit.com", 
            api_key=api_key, 
            api_secret=api_secret,
            spot=False
        )

        self.price_round = {
            "BTCUSDT": 1,
            "ETHUSDT": 2,
            "XRPUSDT": 4
        }

        self.quantity_round = {
            "BTCUSDT": 3,
            "ETHUSDT": 2,
            "XRPUSDT": 0
        }

        self.usdt = 0
        self.long_quantity = 0
        self.short_quantity = 0

    def run(self):
        while True:
            now = datetime.datetime.now()

            if self.main is not None and self.main.ready[self.symbol]:
                # 코인별 포지션별 투자 금액 산정
                self.usdt = self.main.usdt / 6

                # long position
                if self.main.positions[self.symbol][0] == False:
                    self.open_long()
                    self.main.positions[self.symbol][0] = True

                # short position
                if self.main.positions[self.symbol][1] == False:
                    self.open_short()
                    self.main.positions[self.symbol][1] = True

            # 08:59:00 포지션 정리
            if now.hour == 8 and now.minute == 59 and (now.second > 0 and now.second < 10):
                self.close_long()
                self.close_short()
                self.main.ready[self.symbol] = 0    # 9시 전까지는 매매 않하도록
                time.sleep(10)

            # 09:01:00 거래일 파라미터 업데이트 
            if now.hour == 9 and now.minute == 1 and (now.second > 0 and now.second < 10):
                for b in self.main.backtest:
                    b.start()
                time.sleep(10)

            time.sleep(1) 

    def open_long(self):
        """상승장에서 long position open
        """
        target_price = self.main.data[self.symbol]["상승목표가"]
        ndigits = self.price_round[self.symbol]

        qty_round = self.quantity_round[self.symbol]
        order_price = round(target_price, ndigits)

        quantity = self.usdt / order_price
        quantity = round(quantity, qty_round)

        # open the position 
        resp = self.session.place_active_order(
            symbol=self.symbol,
            side="Buy",
            order_type="Limit",
            qty=quantity,
            price=order_price,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False
        )

        # save the quantity
        self.long_quantity = quantity

    def open_short(self):
        """하락장에서 short position open
        """
        target_price = self.main.data[self.symbol]["하락목표가"]
        ndigits = self.price_round[self.symbol]

        qty_round = self.quantity_round[self.symbol]
        order_price = round(target_price, ndigits)

        quantity = self.usdt / order_price
        quantity = round(quantity, qty_round)

        # open the position
        resp = self.session.place_active_order(
            symbol=self.symbol,
            side="Sell",
            order_type="Limit",
            qty=quantity,
            price=order_price,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False
        )

        # save the quantity
        self.short_quantity = quantity

    def close_long(self):
        """long position close
        """
        if self.long_quantity != 0:
            resp = self.session.place_active_order(
                symbol=self.symbol,
                side="Sell",
                order_type="Market",
                qty=self.long_quantity,
                time_in_force="GoodTillCancel",
                reduce_only=True,
                close_on_trigger=False
            )

    def close_short(self):
        """short position close
        """
        if self.short_quantity != 0:
            resp = self.session.place_active_order(
                symbol=self.symbol,
                side="Buy",
                order_type="Market",
                qty=self.short_quantity,
                time_in_force="GoodTillCancel",
                reduce_only=True,
                close_on_trigger=False
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Trader("BTCUSDT")
    w.start()
    app.exec_()