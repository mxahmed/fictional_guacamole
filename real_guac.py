import websocket
import ast
import json
import sqlite3
import os
import datetime
import configparser
import gdax
import sys

config = configparser.ConfigParser()
config.read('config')

class DataFeed():

    def __init__(self):
        url = "wss://ws-feed.gdax.com"
        self.public_client = gdax.PublicClient()
        
        x = ast.literal_eval(config['settings']['product_ids'])
        self.product_ids = [n.strip() for n in x]
        self.order_books = {x:{} for x in self.product_ids}
        self.inside_order_books = {x:{"bids":{},"asks":{}} for x in self.product_ids}
        self.last_trade_ids = {x:None for x in self.product_ids}
        
        file = "websocket_data.db"
        # directory of script being run: os.path.dirname(os.path.abspath(__file__)) vs. current working directory used below
        self.path = os.getcwd()+"/"+file
        self.db = sqlite3.connect(self.path)
        self.cursor = self.db.cursor()
        self.cursor.execute('DROP TABLE IF EXISTS gdax_order_book')
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS gdax_order_book(
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
        self.cursor.execute('DROP TABLE IF EXISTS gdax_trades')
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS gdax_trades(
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
        if msg['type'] == 'snapshot':
            self.order_books[msg['product_id']] = {'bids':msg['bids'],'asks':msg['asks']}
        if msg['type'] == 'l2update':
            changes = msg['changes']
            for change in changes:
                change_side = 'bids' if change[0]=='buy' else 'asks'
                change_price = float(change[1])
                change_volume = float(change[2])
                orders = self.order_books[msg['product_id']][change_side]
                level_index = [i for i, order in enumerate(orders) if float(order[0])==float(change[1])]
                if level_index:
                    if float(change[2]) != 0:
                        self.order_books[msg['product_id']][change_side][min(level_index)][1] = change[2]
                    else:
                        self.order_books[msg['product_id']][change_side].pop(min(level_index))
                if not level_index:
                    if change_side == 'bids':
                        insert_indexes = [i for i, order in enumerate(orders) if float(order[0]) >= float(change[1])]
                    if change_side == 'asks':
                        insert_indexes = [i for i, order in enumerate(orders) if float(order[0]) <= float(change[1])]
                    if not insert_indexes:
                        insert_index = -1
                    else:
                        insert_index = max(insert_indexes)
                    self.order_books[msg['product_id']][change_side].insert(insert_index+1, [change[1],change[2]])
                    
            inside_bids = {'bids_'+str(x+1):"@".join(self.order_books[msg['product_id']]['bids'][x][::-1]) for x in range(15)}
            inside_asks = {'asks_'+str(x+1):"@".join(self.order_books[msg['product_id']]['asks'][x][::-1]) for x in range(15)}
            inside_order_book = {"bids":inside_bids,"asks":inside_asks}
            
            if self.inside_order_books[msg['product_id']] != inside_order_book:
                row = {
                    "server_datetime":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                    "product_id":msg['product_id']
                }
                row.update(inside_bids)
                row.update(inside_asks)
                self.cursor.execute("""INSERT INTO gdax_order_book (server_datetime, 
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
                self.inside_order_books[msg['product_id']] = inside_order_book
                print(row)
            
                        
        if msg['type'] == 'match':
            trades = [{
                "server_datetime":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "exchange_datetime":msg['time'],
                "sequence":msg['sequence'],
                "trade_id":msg['trade_id'],
                "product_id":msg['product_id'],
                'price':msg['price'],
                'volume':msg['size'],
                'side':msg['side'],
                'backfilled':'False'
            }]
            
            current_trade_id = int(msg["trade_id"])
            if self.last_trade_ids[msg["product_id"]]:
                last_trade_id = int(self.last_trade_ids[msg["product_id"]])
            else:
                last_trade_id = current_trade_id
            self.last_trade_ids[msg["product_id"]] = msg["trade_id"]
            if current_trade_id > (last_trade_id + 1):
                missing_trade_ids = list(range(last_trade_id + 1, current_trade_id))
                print("missed the following trades: "+str(missing_trade_ids))
                product_trades = self.public_client.get_product_trades(product_id=msg['product_id'])
                for missing_trade_id in missing_trade_ids:
                    missing_trade_index = [i for i, product_trade in enumerate(product_trades) if int(product_trade['trade_id']) == missing_trade_id][0]
                    missing_product_trade = product_trades[missing_trade_index]
                    missing_trade = {
                            "server_datetime":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"), #2017-10-15T05:10:53.700000Z
                            "exchange_datetime":missing_product_trade['time'],
                            "sequence":"None",
                            "trade_id":missing_product_trade['trade_id'],
                            "product_id":msg['product_id'],
                            'price':missing_product_trade['price'],
                            'volume':missing_product_trade['size'],
                            'side':missing_product_trade['side'],
                            'backfilled':'True'
                    }
                    trades.append(missing_trade)
                
                
            for trade in trades:
                self.cursor.execute("""INSERT INTO gdax_trades (server_datetime, 
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
        request = {
            "type": "subscribe",
            "product_ids": self.product_ids,
                "channels": ["level2","matches"]}
        request = json.dumps(request)
        request = request.encode("utf-8")
        ws.send(request)
        
if __name__ == "__main__":
    DataFeed()