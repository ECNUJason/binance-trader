#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# @yasinkuyu

import sys

sys.path.insert(0, './app')

import time
import config
from datetime import timedelta, datetime
from BinanceAPI import BinanceAPI
import json
import pandas as pd
import numpy as np
from decimal import Decimal

class Binance:

    def __init__(self):
        self.client = BinanceAPI(config.api_key, config.api_secret)

    def balances(self):
        balances = self.client.get_account()
      
        for balance in balances['balances']:
            if float(balance['locked']) > 0 or float(balance['free']) > 0:
                print('%s: %s' % (balance['asset'], balance['free']))

    def balance(self, asset='BTC'):
        balances = self.client.get_account()
        balances['balances'] = {item['asset']: item for item in balances['balances']}
        print(balances['balances'][asset]['free'])

    def orders(self, symbol, limit):
        orders = self.client.get_open_orders(symbol, limit)
        print(orders)

    def tickers(self):
        
        return self.client.get_all_tickers()

    def server_status(self):
        systemT=int(time.time()*1000)           #timestamp when requested was launch
        serverT= self.client.get_server_time()  #timestamp when server replied
        lag=int(serverT['serverTime']-systemT)

        print('System timestamp: %d' % systemT)
        print('Server timestamp: %d' % serverT['serverTime'])
        print('Lag: %d' % lag)

        if lag>1000:
            print('\nNot good. Excessive lag (lag > 1000ms)')
        elif lag<0:
            print('\nNot good. System time ahead server time (lag < 0ms)')
        else:  
            print('\nGood (0ms > lag > 1000ms)')              
        return

    def openorders(self):
        
        return self.client.get_open_orders()

    def profits(self, asset='BTC'):
        coins = self.client.get_products()
        
        for coin in coins['data']:
            if coin['quoteAsset'] == asset:
                orders = self.client.get_order_books(coin['symbol'], 5)             
                if len(orders['bids'])>0 and len(orders['asks'])>0: 
                    lastBid = float(orders['bids'][0][0]) #last buy price (bid)
                    lastAsk = float(orders['asks'][0][0]) #last sell price (ask)
                    
                    if lastBid!=0: 
                        profit = (lastAsk - lastBid) /  lastBid * 100
                    else:
                        profit = 0
                    print('%6.2f%% profit : %s (bid: %.8f / ask: %.8f)' % (profit, coin['symbol'], lastBid, lastAsk))
                else:
                    print('---.--%% profit : %s (No bid/ask info retrieved)' % (coin['symbol']))

    def market_value(self, symbol, kline_size, dateS, dateF="" ):                 
        dateS=datetime.strptime(dateS, "%d/%m/%Y %H:%M:%S")
        
        if dateF!="":
            dateF=datetime.strptime(dateF, "%d/%m/%Y %H:%M:%S")
        else:
            dateF=dateS + timedelta(seconds=59)

        print('Retrieving values...\n')    
        klines = self.client.get_klines(symbol, kline_size, int(dateS.timestamp()*1000), int(dateF.timestamp()*1000))

        if len(klines)>0:
            for kline in klines:
                print('[%s] Open: %s High: %s Low: %s Close: %s' % (datetime.fromtimestamp(kline[0]/1000), kline[1], kline[2], kline[3], kline[4]))

        return
    def past_24_hours(self):
        
        array_data = []
        dict_data = {}
        for coin in self.client.get_past_24_hours():
            symbol = coin['symbol']
            price = Decimal(coin['lastPrice'])
            if symbol.endswith("USDT"):
                array_data.append([symbol, price])
                dict_data[symbol] = price
        np_array = np.array(array_data)
        np_array = np_array[np_array[:, 1].argsort()]
        file_name = "past_24_hours_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        csv_file_name = "{}.csv".format(file_name)
        csv_file_path = "data/{}".format(csv_file_name)
        with open(csv_file_path, 'wb') as csv_file:
            np.savetxt(csv_file, np_array, delimiter=",", fmt='%s', header='symbol,price')
        print("Write 24 hours data to csv file:{}".format(csv_file_path))
        return dict_data
try:
    # List of dictionaries.
    # delayInSeconds = 30 # for debug, set to 10, prod as 60
    delayInSeconds = 60 # normal
    # testInMin = 3 # for debug, set to 1, normal set as 25
    testInMin = 25 # normal
    history_data = []
    m = Binance()
    round = 1
    while True:
        try:
            print("\n\nRound: {}, ----------------- \n\n".format(round))
            round += 1
            past24Hours = m.past_24_hours()
            history_data.append(past24Hours)
            if len(history_data) > testInMin:
                for symbol in past24Hours.keys():
                    currentPrice = past24Hours[symbol]
                    oldPrice = history_data[len(history_data) - testInMin][symbol]
                    if oldPrice != 0:
                        if (currentPrice - oldPrice)/oldPrice > 0.1999:
                            print("Symbol: {}, 30 mins, +20%, currentPrice:{}, oldPrice:{}".format(symbol, currentPrice, oldPrice))
                        elif (currentPrice - oldPrice)/oldPrice > 0.1499:
                            print("Symbol: {}, 30 mins, +15%, currentPrice:{}, oldPrice:{}".format(symbol, currentPrice, oldPrice))
                        elif (currentPrice - oldPrice)/oldPrice > 0.0999:
                            print("Symbol: {}, 30 mins, +10%, currentPrice:{}, oldPrice:{}".format(symbol, currentPrice, oldPrice))
                        # elif (currentPrice - oldPrice)/oldPrice > 0.00001: # For debug
                        #     print("Symbol: {}, 30 mins, +1%, currentPrice:{}, oldPrice:{}".format(symbol, currentPrice, oldPrice))
            if len(history_data) > 40:
                history_data = history_data[1:]
            print("start sleep 60 seconds")
            time.sleep(delayInSeconds)
            print("finished sleep 60 seconds")
        except Exception as e:
            print('Exception in round {}: {}'.format(round, e))

except Exception as e:
    print('Exception: %s' % e)
