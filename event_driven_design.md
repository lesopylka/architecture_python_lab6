# Event-Driven Architecture Design

- [Event-Driven Architecture Design](#event-driven-architecture-design)
  - [Описание системы](#описание-системы)
- [Команды и события](#команды-и-события)
  - [Команды](#команды)
  - [События](#события)
- [Producers](#producers)
- [Consumers](#consumers)
- [RabbitMQ](#rabbitmq)
- [Exchange](#exchange)
- [Routing Keys](#routing-keys)
- [Формат события](#формат-события)
- [Поток событий](#поток-событий)
- [CQRS](#cqrs)
  - [Write model](#write-model)
  - [Read model](#read-model)
- [Гарантии доставки](#гарантии-доставки)
- [Docker](#docker)
- [Проверка работы](#проверка-работы)
- [Вывод](#вывод)


## Описание системы

В проекте реализована Event-Driven архитектура для социальной сети.

В системе есть:

- пользователи
- посты
- сообщения
- лайки
- комментарии

После выполнения действий сервисы публикуют события в RabbitMQ.

 

# Команды и события

## Команды

Команды изменяют состояние системы:

- CreateUser
- CreatePost
- SendMessage
- LikePost
- AddComment

## События

После выполнения команд возникают события:

- UserCreated
- PostCreated
- MessageSent
- PostLiked
- CommentAdded

 

# Producers

Сервисы, публикующие события:

- user-service
- wall-service
- chat-service

В проекте producer реализован в [event-service/producer.py](event-service/producer.py)

# Consumers

Сервисы, обрабатывающие события:

- notification-service
- analytics-service
- read-model-service

В проекте consumer реализован  [event-service/producer.py](event-service/producer.py)

 

# RabbitMQ

В качестве брокера сообщений используется RabbitMQ.

Причины выбора:

- простой запуск через Docker
- поддержка routing keys
- удобная работа с очередями
- подходит для Event-Driven архитектуры

 

# Exchange

Используется exchange:

```text
social.events
```

Тип exchange:

```text
topic
```

 

# Routing Keys

```text
user.created
post.created
message.sent
post.liked
comment.added
```

 

# Формат события

События передаются в формате JSON.

Пример:

```json
{
  "event_id": "uuid",
  "event_type": "UserCreated",
  "occurred_at": "2026-05-19T10:00:00Z",
  "producer": "user-service",
  "payload": {
    "user_id": "u-1",
    "login": "alice"
  }
}
```

 

# Поток событий

Пример работы системы:

1. Пользователь создаёт пост
2. wall-service сохраняет данные
3. Producer публикует событие `PostCreated`
4. RabbitMQ отправляет событие consumer
5. Consumer обрабатывает событие
6. Обновляется read model

 

# CQRS

В проекте используется подход CQRS.

## Write model

Write model отвечает за изменение данных:

- создание пользователей
- создание постов
- отправка сообщений
- лайки
- комментарии

## Read model

Read model используется для чтения данных и статистики.

Коллекции read model:

- `user_activity_view`
- `post_activity_view`

Read model обновляется через события RabbitMQ.

 

# Гарантии доставки

Используется стратегия at-least-once

Для этого используются:

- durable queues
- persistent messages
- manual ack

Consumer сохраняет `event_id`, чтобы избежать повторной обработки событий.

 

# Docker

RabbitMQ запускается через Docker Compose.

Используемые сервисы:

- rabbitmq
- event_producer
- event_consumer

 

# Проверка работы

Запуск consumer:

```bash
docker compose up --build mongo rabbitmq event_consumer
```

Запуск producer:

```bash
docker compose run --rm event_producer
```

Проверка MongoDB:

```bash
docker exec -it social-network-mongo mongosh
```

```bash
use social_network_mongo

db.processed_events.find()

db.user_activity_view.find()

db.post_activity_view.find()
```

# Вывод

В ходе работы была спроектирована Event-Driven архитектура с использованием RabbitMQ.

Были реализованы:

- producer
- consumer
- exchange и routing keys
- CQRS
- обработка событий
- синхронизация read model через события