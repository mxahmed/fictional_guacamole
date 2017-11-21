import websocket
import ast
import json
import sqlite3
import os
import datetime
import configparser
import sys

config = configparser.ConfigParser()
config.read('polo_config')

class DataFeed():

    def __init__(self):
        url = "wss://api2.poloniex.com"
        #self.public_client = polo.PublicClient()
        
        x = ast.literal_eval(config['settings']['product_ids'])
        self.product_ids = [n.strip() for n in x]
        self.product_codes = {}
        self.order_books = {x:{} for x in self.product_ids}
        self.inside_order_books = {x:{"bids":{},"asks":{}} for x in self.product_ids}
        self.last_trade_ids = {x:None for x in self.product_ids}
        
        file = "websocket_data.db"
        # directory of script being run: os.path.dirname(os.path.abspath(__file__)) vs. current working directory used below
        self.path = os.getcwd()+"/"+file
        self.db = sqlite3.connect(self.path)
        self.cursor = self.db.cursor()
        self.cursor.execute('DROP TABLE IF EXISTS polo_order_book')
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS polo_order_book(
            server_datetime TEXT,
            product_id TEXT,
            bids_1 TEXT,
            bids_2 TEXT,
            bids_3 TEXT,
            bids_4 TEXT,
            bids_5 TEXT,
            bids_6 TEXT,
            bids_7 TEXT,
            bids_8 TEXT,
            bids_9 TEXT,
            bids_10 TEXT,
            bids_11 TEXT,
            bids_12 TEXT,
            bids_13 TEXT,
            bids_14 TEXT,
            bids_15 TEXT,
            asks_1 TEXT,
            asks_2 TEXT,
            asks_3 TEXT,
            asks_4 TEXT,
            asks_5 TEXT,
            asks_6 TEXT,
            asks_7 TEXT,
            asks_8 TEXT,
            asks_9 TEXT,
            asks_10 TEXT,
            asks_11 TEXT,
            asks_12 TEXT,
            asks_13 TEXT,
            asks_14 TEXT,
            asks_15 TEXT
               )""")
        self.cursor.execute('DROP TABLE IF EXISTS polo_trades')
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS polo_trades(
            server_datetime TEXT,
            exchange_datetime TEXT,
            sequence TEXT,
            trade_id TEXT,
            product_id TEXT,
            price TEXT,
            volume TEXT,
            side TEXT,
            backfilled TEXT
            )""")
        self.db.commit()
        
        self.ws = websocket.WebSocketApp(url,
                                         on_message=self.on_message,
                                         on_error=self.on_error
                                         )
        self.ws.on_open = self.on_open
        while True:
            try:
                self.ws.run_forever()
            except Exception:
                pass
            except KeyboardInterrupt:
                sys.exit()
                
        
    def on_message(self,ws,msg):
        msg = ast.literal_eval(msg) #convert string to list
        #print(msg)
        for message in msg[2]: #maybe will be better if current implementation doesn't work
            if message[0] == 'i':
                print("got ob snapshot")
                self.order_books[message[1]['currencyPair']] = {'bids':[[x, message[1]['orderBook'][1][x]] for x in message[1]['orderBook'][1]],'asks':[[x, message[1]['orderBook'][0][x]] for x in message[1]['orderBook'][0]]}
                self.product_codes[msg[0]] = message[1]['currencyPair']
            elif message[0] == 'o':
                change_side = 'bids' if message[1]==1 else 'asks'
                orders = self.order_books[self.product_codes[msg[0]]][change_side]
                level_index = [i for i, order in enumerate(orders) if float(order[0])==float(message[2])]
                if level_index:
                    if float(message[3]) != 0:
                        self.order_books[self.product_codes[msg[0]]][change_side][min(level_index)][1] = message[3]
                    else:
                        self.order_books[self.product_codes[msg[0]]][change_side].pop(min(level_index))
                if not level_index:
                    if change_side == 'bids':
                        insert_indexes = [i for i, order in enumerate(orders) if float(order[0]) >= float(message[1])]
                    if change_side == 'asks':
                        insert_indexes = [i for i, order in enumerate(orders) if float(order[0]) <= float(message[1])]
                    if not insert_indexes:
                        insert_index = -1
                    else:
                        insert_index = max(insert_indexes)
                    self.order_books[self.product_codes[msg[0]]][change_side].insert(insert_index+1, [message[2],message[3]])
                        
                inside_bids = {'bids_'+str(x+1):"@".join(self.order_books[self.product_codes[msg[0]]]['bids'][x][::-1]) for x in range(15)}
                inside_asks = {'asks_'+str(x+1):"@".join(self.order_books[self.product_codes[msg[0]]]['asks'][x][::-1]) for x in range(15)}
                inside_order_book = {"bids":inside_bids,"asks":inside_asks}
                
                if self.inside_order_books[self.product_codes[msg[0]]] != inside_order_book:
                    row = {
                        "server_datetime":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%Z"),
                        "product_id":self.product_codes[msg[0]]
                    }
                    row.update(inside_bids)
                    row.update(inside_asks)
                    self.cursor.execute("""INSERT INTO polo_order_book (server_datetime, 
                    product_id, 
                    bids_1, 
                    bids_2, 
                    bids_3, 
                    bids_4, 
                    bids_5, 
                    bids_6, 
                    bids_7, 
                    bids_8, 
                    bids_9, 
                    bids_10, 
                    bids_11, 
                    bids_12, 
                    bids_13, 
                    bids_14, 
                    bids_15, 
                    asks_1, 
                    asks_2, 
                    asks_3, 
                    asks_4, 
                    asks_5, 
                    asks_6, 
                    asks_7, 
                    asks_8, 
                    asks_9, 
                    asks_10, 
                    asks_11, 
                    asks_12, 
                    asks_13, 
                    asks_14, 
                    asks_15) 
                    VALUES (:server_datetime, 
                    :product_id, 
                    :bids_1, 
                    :bids_2, 
                    :bids_3, 
                    :bids_4, 
                    :bids_5, 
                    :bids_6, 
                    :bids_7, 
                    :bids_8, 
                    :bids_9, 
                    :bids_10, 
                    :bids_11, 
                    :bids_12, 
                    :bids_13, 
                    :bids_14, 
                    :bids_15, 
                    :asks_1, 
                    :asks_2, 
                    :asks_3, 
                    :asks_4, 
                    :asks_5, 
                    :asks_6, 
                    :asks_7, 
                    :asks_8, 
                    :asks_9, 
                    :asks_10, 
                    :asks_11, 
                    :asks_12, 
                    :asks_13, 
                    :asks_14, 
                    :asks_15);""", row)
                    self.db.commit()
                    self.inside_order_books[self.product_codes[msg[0]]] = inside_order_book
                    print(row)
                
                            
            elif message[0] == 't':
                # TRADES
                # ["t","9394200",1,"5545.00000000","0.00009541",1508060546]
                # [trade, tradeId, 0/1 (sell/buy), price, amount, timestamp]
                #print(message)
                trades = [{
                    "server_datetime":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%Z"),
                    "exchange_datetime":datetime.datetime.fromtimestamp(message[5]).strftime("%Y-%m-%dT%H:%M:%S.%f%Z"),
                    "sequence":msg[1],
                    "trade_id":message[1],
                    "product_id":self.product_codes[msg[0]],
                    'price':message[3],
                    'volume':message[4],
                    'side':'sell' if message[2]==0 else 'buy',
                    'backfilled':'False'
                }]
                
                current_trade_id = int(message[1])
                if self.last_trade_ids[self.product_codes[msg[0]]]:
                    last_trade_id = int(self.last_trade_ids[self.product_codes[msg[0]]])
                else:
                    last_trade_id = current_trade_id
                self.last_trade_ids[self.product_codes[msg[0]]] = message[1]
                if current_trade_id > (last_trade_id + 1):
                    missing_trade_ids = list(range(last_trade_id + 1, current_trade_id))
                    print("missed the following trades: "+str(missing_trade_ids))
                    
                    
                for trade in trades:
                    self.cursor.execute("""INSERT INTO polo_trades (server_datetime, 
                    exchange_datetime, 
                    sequence,
                    trade_id,
                    product_id,
                    price,
                    volume,
                    side,
                    backfilled
                    ) 
                    VALUES (:server_datetime, 
                    :exchange_datetime, 
                    :sequence, 
                    :trade_id,
                    :product_id,
                    :price,
                    :volume,
                    :side,
                    :backfilled
                    );""", trade)
                    self.db.commit()
                    print(trade)
        

    def on_error(self,ws,error):
        print(error)
        
    def on_open(self,ws):
        #request = {
        #    "type": "subscribe",
        #    "channel": "BTC_ETH"}
        #request = json.dumps(request)
        #request = request.encode("utf-8")
        for x in self.product_ids:
            ws.send(json.dumps({'command':'subscribe','channel':x}))
        #ws.send(request)
        
if __name__ == "__main__":
    DataFeed()
    
    
# https://stackoverflow.com/questions/32154121/how-to-connect-to-poloniex-com-websocket-api-using-a-python-library

#1001 = trollbox (you will get nothing but a heartbeat)
#1002 = ticker
#1003 = base coin 24h volume stats
#1010 = heartbeat
#'MARKET_PAIR' = market order books

# ORDERBOOK SNAPSHOT
# [114,247989292,[["i",{"currencyPair":"BTC_XMR","orderBook":[{"0.01629561":"2.32977526","0.01629618":"14.77417529",
# orderbook[0] = asks, orderbook[1] = bids (inferred from pricing: 0 is increasing price from middle, 1 is decreasing price from middle)

# ORDERS
#  [148,394056638,[["o",0,"0.07615527","0.34317849"]]]
# 148: appears to be the ID of the Currency Pair.
# 394056638: Sequence number (I presume of the last sequence value prior to the full orderbook as presented) 
# "o" + 0: orderBookRemove "o" + 1: orderBookModify 
# "0.07615527": Price 
# "0.34317849": Quantity

# TRADES
# ["t","9394200",1,"5545.00000000","0.00009541",1508060546]
# [trade, tradeId, 0/1 (sell/buy), price, amount, timestamp]