from typing import Dict, List
from itertools import islice
from config import config
from loguru import logger
from quixstreams import Application
from src.kraken_api.trade import Trade
import json

def produce_trades(
    kafka_broker: str, 
    kafka_topic_name: str, 
    product_ids: List[str],
    live_or_historical:str,
    last_n_days:int
) -> None:
    """
    Produce a stream of random trades to a Kafka topic.

    :param kafka_broker: The address of the Kafka broker.
    :param kafka_topic: The name of the Kafka topic to write to.
    """

    app = Application(broker_address=kafka_broker)
    output_topic = app.topic(name=kafka_topic_name, value_serializer='json', key_serializer='string')
    logger.info('Connecting to Kraken API...')

    if live_or_historical == 'live':
        from kraken_api.websocket import KrakenwebsocketTradeAPI
        kraken_api = KrakenwebsocketTradeAPI(product_ids=product_ids)

    else:
        from kraken_api.rest import KrakenRestAPIMultipleProducts 
        kraken_api = KrakenRestAPIMultipleProducts(product_ids, last_n_days)
    
    while True:
        trades: List[Trade] = kraken_api.get_trades()
        
        for trade in trades:
            
            with app.get_producer() as producer:
                
                # We overwrite the timestamp so later we can calculate the OHLC window.
                message = output_topic.serialize(
                    key=trade.product_id,  # Directly encode the product_id
                    value=dict(trade),   
                )
                
                # Produce a message into the kafka topic.
                producer.produce(
                    topic=output_topic.name, 
                    value=message.value, 
                    key=message.key,
                    timestamp=trade.timestamp_ms #Trade timestamp, not upload timestamp
                )
                if live_or_historical == 'live':
                    logger.info(f'Produced trade: {trade} to topic: {output_topic.name}')
                
            #If we are running the backfill pipeline, we only want to fetch the data once
        if live_or_historical == 'historical':
            break
            
if __name__ == '__main__':

    produce_trades(
        config.kafka_broker_address, 
        config.kafka_output_topic,
        config.product_ids,
        config.live_or_historical,
        config.last_n_days
    )
