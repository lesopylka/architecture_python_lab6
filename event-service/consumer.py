import json
import os
import time

import pika
from pymongo import MongoClient


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "social_network_mongo")

EXCHANGE_NAME = "social.events"
QUEUE_NAME = "read-model.events"


mongo_client = MongoClient(MONGO_URL)
db = mongo_client[MONGO_DB]


def connect_rabbitmq():
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            return pika.BlockingConnection(params)
        except Exception:
            print("RabbitMQ is not ready, retrying...")
            time.sleep(2)


def process_event(event):
    event_id = event["event_id"]
    event_type = event["event_type"]
    payload = event["payload"]

    exists = db.processed_events.find_one({"event_id": event_id})
    if exists:
        print(f"Duplicate event ignored: {event_id}")
        return

    db.processed_events.insert_one({
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": event["occurred_at"],
        "producer": event["producer"],
        "payload": payload,
    })

    if event_type == "UserCreated":
        db.user_activity_view.update_one(
            {"user_id": payload["user_id"]},
            {
                "$set": {
                    "user_id": payload["user_id"],
                    "login": payload["login"],
                    "email": payload["email"],
                },
                "$setOnInsert": {
                    "posts_count": 0,
                    "messages_sent": 0,
                    "likes_received": 0,
                    "comments_count": 0,
                },
            },
            upsert=True,
        )

    elif event_type == "PostCreated":
        db.user_activity_view.update_one(
            {"user_id": payload["author_id"]},
            {
                "$inc": {
                    "posts_count": 1,
                }
            },
            upsert=True,
        )

    elif event_type == "MessageSent":
        db.user_activity_view.update_one(
            {"user_id": payload["from_user_id"]},
            {
                "$inc": {
                    "messages_sent": 1,
                }
            },
            upsert=True,
        )

    elif event_type == "PostLiked":
        db.post_activity_view.update_one(
            {"post_id": payload["post_id"]},
            {
                "$set": {
                    "post_id": payload["post_id"],
                },
                "$inc": {
                    "likes_count": 1,
                },
            },
            upsert=True,
        )

    elif event_type == "CommentAdded":
        db.post_activity_view.update_one(
            {"post_id": payload["post_id"]},
            {
                "$set": {
                    "post_id": payload["post_id"],
                },
                "$inc": {
                    "comments_count": 1,
                },
            },
            upsert=True,
        )

    print(f"Processed event: {event_type}")


def callback(channel, method, properties, body):
    try:
        event = json.loads(body)
        process_event(event)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Failed to process event: {e}")
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )


def main():
    connection = connect_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    routing_keys = [
        "user.*",
        "post.*",
        "message.*",
        "comment.*",
    ]

    for routing_key in routing_keys:
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key=routing_key,
        )

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=False,
    )

    print("Consumer started. Waiting for events...")
    channel.start_consuming()


if __name__ == "__main__":
    main()