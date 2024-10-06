from src.config import config
from loguru import logger
from datetime import timedelta
import time

def trade_to_ohlc(
    kafka_input_topic: str,
    kafka_output_topic: str,
    kafka_broker: str, 
    ohlc_window_seconds,
    consumer_group: str
) -> None:
    """
    Consume trades from a Kafka topic, aggregates them using 
    tumbling window and produce candle data to a new Kafka topic.

    :param kafka_broker: The address of the Kafka broker.
    :param kafka_topic_name: The name of the Kafka topic to read from.
    :param product_id: The product ID to filter trades by.
    :param consumer_group: The Kafka consumer group to use.
    :return: None
    """

    from quixstreams import Application
    # Create a new Quix application.
    app = Application(
        broker_address=kafka_broker, 
        consumer_group=consumer_group,
        auto_offset_reset='latest'
    )

    input_topic = app.topic(name=kafka_input_topic, value_deserializer='json', key_deserializer='string')
    output_topic = app.topic(name=kafka_output_topic, value_serializer='json', key_serializer='string')

    
    # Initialize the OHLC candle
    def initialize_ohlc_candle(value:dict) -> dict:
        
        return {
            'product_id': value['product_id'],
            'open': value['price'],
            'high': value['price'],
            'low': value['price'],
            'close': value['price'],
        }
    
    #Reducer function to update the OHLC candle
    def update_ohlc_candle(ohlc_candle:dict, trade:dict) -> dict:
        
        return {
            'product_id': trade['product_id'],
            'open': ohlc_candle['open'],
            'high': max(ohlc_candle['high'], trade['price']),
            'low': min(ohlc_candle['low'], trade['price']),
            'close': trade['price'],
        }
    
    sdf = app.dataframe(input_topic)
  
    sdf = sdf.tumbling_window(duration_ms = timedelta(seconds = ohlc_window_seconds))
    sdf = sdf.reduce(reducer = update_ohlc_candle, initializer = initialize_ohlc_candle).final()

    sdf['product_id'] = sdf['value']['product_id']
    sdf['open'] = sdf['value']['open']
    sdf['high'] = sdf['value']['high']
    sdf['low'] = sdf['value']['low']
    sdf['close'] = sdf['value']['close']
    sdf['timestamp'] = sdf['end']
    sdf = sdf[['timestamp', 'product_id', 'open', 'high', 'low', 'close']]
    
    sdf.update(logger.info)
    sdf = sdf.to_topic(output_topic)
    logger.info(sdf)
    # Start the application
    app.run(sdf)


if __name__ == '__main__':
    
    trade_to_ohlc(
        kafka_input_topic= config.kafka_input_topic_name,
        kafka_output_topic= config.kafka_output_topic_name,
        kafka_broker= config.kafka_broker_address,
        ohlc_window_seconds= config.ohlc_window_seconds,
        consumer_group= config.consumer_group
    )