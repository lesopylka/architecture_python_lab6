import json
import os
import time
import uuid
from datetime import datetime, timezone

import pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = "social.events"


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            return pika.BlockingConnection(params)
        except Exception:
            print("RabbitMQ is not ready, retrying...")
            time.sleep(2)


def publish_event(channel, routing_key, event_type, producer, payload):
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": now(),
        "producer": producer,
        "payload": payload,
    }

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=routing_key,
        body=json.dumps(event),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )

    print(f"Published {event_type}: {event}")


def main():
    connection = connect()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )

    publish_event(
        channel=channel,
        routing_key="user.created",
        event_type="UserCreated",
        producer="user-service",
        payload={
            "user_id": "u-1",
            "login": "alice",
            "email": "alice@example.com",
            "created_at": now(),
        },
    )

    publish_event(
        channel=channel,
        routing_key="post.created",
        event_type="PostCreated",
        producer="wall-service",
        payload={
            "post_id": "p-1",
            "author_id": "u-1",
            "content": "Hello from Event-Driven architecture",
            "tags": ["event-driven", "rabbitmq"],
            "created_at": now(),
        },
    )

    publish_event(
        channel=channel,
        routing_key="message.sent",
        event_type="MessageSent",
        producer="chat-service",
        payload={
            "message_id": "m-1",
            "from_user_id": "u-1",
            "to_user_id": "u-2",
            "text": "Hello!",
            "created_at": now(),
        },
    )

    publish_event(
        channel=channel,
        routing_key="post.liked",
        event_type="PostLiked",
        producer="wall-service",
        payload={
            "post_id": "p-1",
            "user_id": "u-2",
            "liked_at": now(),
        },
    )

    publish_event(
        channel=channel,
        routing_key="comment.added",
        event_type="CommentAdded",
        producer="wall-service",
        payload={
            "post_id": "p-1",
            "user_id": "u-2",
            "comment_id": "c-1",
            "text": "Nice post!",
            "created_at": now(),
        },
    )

    connection.close()


if __name__ == "__main__":
    main()