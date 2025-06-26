import pika
import time
import json

def clock_master(tick_interval=30):
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Dichiarazione exchange fanout
    channel.exchange_declare(exchange="tick_exchange", exchange_type="fanout")

    tick_count = 0
    while True:
        message = {"tick": tick_count}
        # Pubblica sul fanout exchange (routing_key vuota)
        channel.basic_publish(exchange="tick_exchange", routing_key="", body=json.dumps(message))
        print(f"[CLOCK] Tick {tick_count} inviato")
        tick_count += 1
        time.sleep(tick_interval)

if __name__ == "__main__":
    clock_master()
