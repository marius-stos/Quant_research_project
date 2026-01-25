import os
import numpy as np
import pandas as pd
from datetime import datetime
import backtrader as bt

# set browser full width (fix import for Python 3.12)
from IPython.display import display, HTML
display(HTML("<style>.container { width:100% !important; }</style>"))

class BollingerBands(bt.Strategy):
    params = (
        ('n', 20),
        ('ndev', 2.0),
        ('printlog', False),
    )

    def __init__(self):
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.bar_executed = None
        self.val_start = None
        self.dataclose = self.datas[0].close
        self.bollinger = bt.indicators.BollingerBands(self.dataclose, period=self.params.n, devfactor=self.params.ndev)
        self.mb = self.bollinger.mid
        self.ub = self.bollinger.top
        self.lb = self.bollinger.bot

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.val_start = self.broker.get_cash()

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.0f, Cost: %.2f, Comm %.2f, RemSize: %.0f, RemCash: %.2f' %
                    (order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                     order.executed.remsize,
                     self.broker.get_cash()))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log('SELL EXECUTED, Price: %.2f, Size: %.0f, Cost: %.2f, Comm %.2f, RemSize: %.0f, RemCash: %.2f' %
                         (order.executed.price,
                          order.executed.size,
                          order.executed.value,
                          order.executed.comm,
                          order.executed.remsize,
                          self.broker.get_cash()))
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Expired, order.Margin, order.Rejected]:
            self.log('Order Failed')

        self.order = None

    def next(self):
        if self.order:
            return

        if np.count_nonzero(~np.isnan(self.mb.get(0, len(self.mb)))) == 1:
            return

        if self.position.size <= 0 \
                and self.dataclose[0] > self.lb[0] \
                and self.dataclose[-1] < self.lb[-1]:
            self.order = self.buy()

        elif self.position.size >= 0 \
                and self.dataclose[0] < self.ub[0] \
                and self.dataclose[-1] > self.ub[-1]:
            self.order = self.sell()

        elif self.dataclose[0] < self.mb[0] and self.position.size < 0:
            self.order = self.buy()

        elif self.dataclose[0] > self.mb[0] and self.position.size > 0:
            self.order = self.sell()

    def stop(self):
        roi = (self.broker.get_value() / self.val_start) - 1.0
        self.log('ROI: {:.2f}%'.format(100.0 * roi))
        self.log('(Bollinger params (%2d, %2d)) Ending Value %.2f' %
                 (self.params.n, self.params.ndev, self.broker.getvalue()), doprint=True)


if __name__ == '__main__':
    param_opt = False
    perf_eval = True
    benchmark = 'SPX'

    cerebro = bt.Cerebro()

    # 
    datapath = "/Users/mariusstos/quant_research_project/data/SPX.csv"

    # Create a Data Feed
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        fromdate=datetime(2010, 1, 1),
        todate=datetime(2019, 12, 31),
        reverse=False)

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.PercentSizerInt, percents=95)
    cerebro.broker.setcommission(commission=0.001)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    if param_opt:
        cerebro.optstrategy(BollingerBands, n=[10, 20], ndev=[2.0, 2.5])
        perf_eval = False
    else:
        cerebro.addstrategy(BollingerBands, n=20, ndev=2.0, printlog=True)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DrawDown')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    results = cerebro.run()
    strat = results[0]

    print('Final Portfolio Value: %.2f, Sharpe Ratio: %.2f, DrawDown: %.2f, MoneyDown %.2f' %
          (cerebro.broker.getvalue(),
           strat.analyzers.SharpeRatio.get_analysis()['sharperatio'],
           strat.analyzers.DrawDown.get_analysis()['drawdown'],
           strat.analyzers.DrawDown.get_analysis()['moneydown']))

    if perf_eval:
        import matplotlib.pyplot as plt
        cerebro.plot(style='candlestick')
        plt.show()
