from typing import List, Dict, Tuple

from datetime import timezone, datetime
import requests

class KrakenRestAPI:

    def __init__(
        self,
        product_ids: List[str],
        last_n_days: int,
    )-> None:
        """
        Initialize the Kraken API REST client.
        Params:
            product_ids (List[str]): List of product IDs to fetch data for.
            last_n_days (int): Number of days in the past to fetch data from.
        Attributes:
            to_ms (int): Current date in milliseconds since epoch.
            from_ms (int): Start date in milliseconds since epoch, calculated based on `last_n_days`.
            last_trade_ms (int): Timestamp of the last trade in milliseconds since epoch.
            product_ids (List[str]): List of product IDs to fetch data for.
            is_finished (bool): Flag indicating whether the data fetching is finished.
        """
        
        
        # Time related parameters
        today_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.to_ms = int(today_date.timestamp() * 1000)
        self.from_ms = self.to_ms - last_n_days * 24 * 60 * 60 * 1000
        self.last_trade_ms = self.from_ms

        self.product_ids = product_ids
        self.is_finished = False
        


    def get_trades(self) -> List[Dict]:

        payload = {}
        headers = {'Accept': 'application/json'}

        since_sec = self.last_trade_ms // 1000
        url = f'https://api.kraken.com/0/public/Trades?pair={self.product_ids[0]}&since={since_sec}'

        data = requests.get(url, params=payload, headers=headers).json()
    
        trades = [
            {
                'price': float(trade[0]),
                'volume': float(trade[1]),
                'time': int(trade[2]),
                'product_id': self.product_ids[0]
            }
            for trade in data['result'][self.product_ids[0]]
        ]

        #Filter out trades that are after the end timestamp
        trades = [trade for trade in trades if trade['time'] <= self.to_ms // 1000]

        #Update the last trade timestamp
        last_tx_in_ns = int(data['result']['last'])
        self.last_trade_ms = last_tx_in_ns // 1000000

        #Update flag attribute
        self.is_finished = self.last_trade_ms >= self.to_ms   
                 
        return trades
    
  