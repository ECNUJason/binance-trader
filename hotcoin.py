#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# @yasinkuyu

import sys

sys.path.insert(0, './app')

import os.path
import os
import time
import config
from datetime import datetime
import numpy as np
from decimal import Decimal
import logging

from Mailer import Mailer
from BinanceAPI import BinanceAPI
import traceback

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


    def past_24_hours(self, logger, mailer):
        array_data = []
        dict_data = {}
        response = self.client.get_past_24_hours()
        response_string = "{}".format(response)
        error_msg = "Way too much request weight used"
        if error_msg in response_string:
            logger.warning(error_msg)
            mailer.send_email(error_msg, logger)
            raise Exception("throtting triggered.")
        for coin in response:
            symbol = coin['symbol']
            # price = Decimal(coin['lastPrice'])
            price = Decimal(coin['bidPrice'])
            if symbol.endswith("USDT"):
                array_data.append([symbol, price])
                dict_data[symbol] = price
            # if symbol == 'COCOSUSDT':
            #     print("check price:{}".format(coin))
        np_array = np.array(array_data)
        np_array = np_array[np_array[:, 1].argsort()]
        file_name = "past_24_hours_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        csv_file_name = "{}.csv".format(file_name)
        csv_file_path = "data/{}".format(csv_file_name)
        with open(csv_file_path, 'wb') as csv_file:
            np.savetxt(csv_file, np_array, delimiter=",", fmt='%s', header='symbol,price')
        # logger.info("Write 24 hours data to csv file:{}".format(csv_file_path))
        return dict_data
    
    def prepare_logger(self):
        # 第一步，创建一个logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)  # Log等级总开关
        # 第二步，创建一个handler，用于写入日志文件
        rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
        log_path = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(log_path):
            os.mkdir(log_path)
        log_name = os.path.join(log_path, rq + '.log')
        logfile = log_name
        fh = logging.FileHandler(logfile, mode='w')
        fh.setLevel(logging.INFO)  # 输出到file的log等级的开关
        # 第三步，定义handler的输出格式
        formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        # 第四步，将logger添加到handler里面
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(logging.INFO)  # 输出到console的log等级的开关
        logger.addHandler(ch)
        return logger


    def handle_business(self, businessInMin, past24Hours, history_data, mailer):
        if len(history_data) <= businessInMin:
            return None
        if past24Hours is None:
            return None
        else:
            email_msg = ""
            for symbol in past24Hours.keys():
                currentPrice = past24Hours[symbol]
                if symbol in history_data[len(history_data) - businessInMin - 1].keys():
                    oldPrice = history_data[len(history_data) - businessInMin - 1][symbol]
                    if oldPrice != 0:
                        ratio = ((currentPrice - oldPrice)/oldPrice) # To avoid ratio become 0
                        ratio = round(ratio, 5)
                        if ratio > 0.1999:
                            msg = "=====================> Symbol: {}, {} mins, +20%, ratio:{}, currentPrice:{}, oldPrice:{}".format(symbol, businessInMin, ratio, currentPrice, oldPrice)
                            email_msg = "{}\n{}".format(email_msg, msg)
                            logger.info(msg)
                        elif ratio > 0.1499:
                            msg = "=====================> Symbol: {}, {} mins, +15%, ratio:{}, currentPrice:{}, oldPrice:{}".format(symbol, businessInMin, ratio, currentPrice, oldPrice)
                            email_msg = "{}\n{}".format(email_msg, msg)
                            logger.info(msg)
                        elif ratio > 0.0999:
                            msg = "=====================> Symbol: {}, {} mins, +10%, ratio:{}, currentPrice:{}, oldPrice:{}".format(symbol, businessInMin, ratio, currentPrice, oldPrice)
                            email_msg = "{}\n{}".format(email_msg, msg)
                            logger.info(msg)

                        if businessInMin <= 3:
                            if ratio >= 0.0399:
                                msg = "=====================> Symbol: {}, {} mins, +4%, ratio:{}, currentPrice:{}, oldPrice:{}".format(symbol, businessInMin, ratio, currentPrice, oldPrice)
                                email_msg = "{}\n{}".format(email_msg, msg)
                                logger.info(msg)
            if len(email_msg) > 0:
                return email_msg
            else:
                return None


    def sleepInSeconds(self, logger, delayInSeconds):
        logger.info("sleep for {} seconds".format(delayInSeconds))
        time.sleep(delayInSeconds)
    

    def concat_email_msg(self, currentMsg, appendMsg):
        ret = currentMsg
        if appendMsg is not None:
            ret = "{}\n-------\nBusiness:{}".format(currentMsg, appendMsg)
        return ret

    

    def getSystemInfo(self, logger):
        import platform,socket,re,uuid,json,psutil
        try:
            info={}
            info['platform']=platform.system()
            info['platform-release']=platform.release()
            info['platform-version']=platform.version()
            info['architecture']=platform.machine()
            info['hostname']=socket.gethostname()
            info['ip-address']=socket.gethostbyname(socket.gethostname())
            info['mac-address']=':'.join(re.findall('..', '%012x' % uuid.getnode()))
            info['processor']=platform.processor()
            info['ram']=str(round(psutil.virtual_memory().total / (1024.0 **3)))+" GB"
            info['pid']=os.getpid()
            return json.dumps(info)
        except Exception as e:
            logger.exception(e)
            raise e

    def liveness_pulse(self, roundIdx, mailer, logger):
        if roundIdx % 60 == 0:
            mailer.send_email("hourly heart beat from machine:\n{}".format(self.getSystemInfo(logger)), logger, "Liveness Pulse")


try:
    delayInSeconds = 60
    business1Min = 1
    business5Min = 5
    business10Min = 10
    business25Min = 25
    business60Min = 60
    history_data = []
    m = Binance()
    roundIdx = 0
    logger = m.prepare_logger()
    mailer = Mailer()
    while True:
        try:
            m.liveness_pulse(roundIdx, mailer, logger)
            logger.info("Round: {}, -----------------".format(roundIdx))
            roundIdx += 1
            past24Hours = m.past_24_hours(logger, mailer)
            history_data.append(past24Hours)
            email_msg = ""
            email_msg = m.concat_email_msg(email_msg, m.handle_business(business1Min, past24Hours, history_data, mailer))
            email_msg = m.concat_email_msg(email_msg, m.handle_business(business5Min, past24Hours, history_data, mailer))
            email_msg = m.concat_email_msg(email_msg, m.handle_business(business10Min, past24Hours, history_data, mailer))
            email_msg = m.concat_email_msg(email_msg, m.handle_business(business25Min, past24Hours, history_data, mailer))
            email_msg = m.concat_email_msg(email_msg, m.handle_business(business60Min, past24Hours, history_data, mailer))
            if len(email_msg) > 0:
                email_msg = "{}.\n System Info:{}".format(email_msg, m.getSystemInfo(logger))
                email_msg = "Time:{} \n {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), email_msg)
                mailer.send_email(email_msg, logger)
            if len(history_data) > 100:
                history_data = history_data[1:]
            m.sleepInSeconds(logger, delayInSeconds)
        except Exception as e:
            error_msg = 'Exception in roundIdx {}: {}'.format(roundIdx, e)
            logger.error(error_msg)
            traceback.print_exc()
            if len(history_data) > 1:
                history_data.append(history_data[-1]) # use data in last min
            error_msg = "{}\n From machine:\n{}".format(error_msg, m.getSystemInfo(logger))
            mailer.send_email(error_msg, logger, "Error in round:{}".format(roundIdx))
            m.sleepInSeconds(logger, delayInSeconds)

except Exception as e:
    logger.info('Exception: %s' % e)
    traceback.print_exc()
