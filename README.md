# Домашнее задание 06: Проектирование Event-Driven архитектуры
--Цель работы:-- Получить навыки проектирования событийно-ориентированной
архитектуры, работы с брокерами сообщений и применения паттерна CQRS.
--Время выполнения:-- 3-4 часа

- [Домашнее задание 06: Проектирование Event-Driven архитектуры](#домашнее-задание-06-проектирование-event-driven-архитектуры)
  - [Задание](#задание)
- [События](#события)
- [RabbitMQ](#rabbitmq)
- [Producer](#producer)
- [Consumer](#consumer)
- [CQRS](#cqrs)
- [Гарантия доставки](#гарантия-доставки)
- [Запуск](#запуск)
- [Проверка](#проверка)
  - [Проверка producer](#проверка-producer)
  - [Проверка событий:](#проверка-событий)
- [RabbitMQ UI](#rabbitmq-ui)


## Задание
Для своего варианта задания выполните следующие задачи:
1. Анализ событий в системе
 - Изучите выбранный вариант задания
 - Определите события (events), которые происходят в вашей системе
 - Определите команды (commands), которые инициируют события
 - Определите, какие сервисы должны быть уведомлены о каждом событии
2. Проектирование Event-Driven архитектуры
 - Определите компоненты системы, которые будут производителями событий (event
producers)
 - Определите компоненты, которые будут потребителями событий (event consumers)
 - Определите типы событий и их структуру (payload)
 - Опишите поток событий в системе
3. Проектирование взаимодействия через брокер сообщений
 - Выберите RabbitMQ или Apache Kafka
 - Определите формат сообщений для событий
 - Опишите гарантии доставки сообщений (at-least-once, exactly-once)
4. Применение паттерна CQRS
 - Определите, можно ли применить CQRS в вашей системе
 - Если да, разделите операции на команды (write) и запросы (read)
 - Опишите, как события синхронизируют read и write модели
5. Реализация простого Event-Driven сервиса--
 - Настройте RabbitMQ/Kafka (использовать Docker)
 - Реализуйте простой producer, который публикует события
 - Реализуйте простой consumer, который обрабатывает события
 - Протестируйте взаимодействие
6. Документация событий
 - Создайте каталог событий (event catalog) с описанием всех событий
 - Для каждого события укажите:
 - Название события
 - Структуру payload
 - Производителя события
 - Потребителей события

# События

Используются события:

- `UserCreated`
- `PostCreated`
- `MessageSent`
- `PostLiked`
- `CommentAdded`


# RabbitMQ

Exchange:

```text
social.events
````

Тип exchange:

```text
topic
```

Routing keys:

```text
user.created
post.created
message.sent
post.liked
comment.added
```

# Producer

Producer публикует события в RabbitMQ.

Файл:

[event-service/consumer.py](event-service/consumer.py)

 

# Consumer

Consumer получает события и обновляет MongoDB.

Файл:

[event-service/consumer.py](event-service/consumer.py)


Consumer сохраняет:

- обработанные события
- read model
- статистику активности

 

# CQRS

Write model:

- создание пользователей
- создание постов
- отправка сообщений
- лайки
- комментарии

Read model:

- `user_activity_view`
- `post_activity_view`

Read model обновляется асинхронно через события.

 

# Гарантия доставки

Используется at-least-once

Для этого используются:

- durable queues
- persistent messages
- manual ack

 

# Запуск

Запуск MongoDB, RabbitMQ и consumer:

```bash
docker compose up --build mongo rabbitmq event_consumer
```

Запуск producer:

```bash
docker compose run --rm event_producer
```

 

# Проверка

Подключение к MongoDB:

```bash
docker exec -it social-network-mongo mongosh
```

## Проверка producer

Producer успешно публикует события:

- UserCreated
- PostCreated
- MessageSent
- PostLiked
- CommentAdded

После запуска команды:

```bash
docker compose run --rm event_producer
```


## Проверка событий:

Consumer обрабатывает события и сохраняет их в MongoDB.

```bash
use social_network_mongo

db.processed_events.find()

db.user_activity_view.find()

db.post_activity_view.find()
```

 

# RabbitMQ UI

```text
http://localhost:15672
```

Логин:
```text
guest
```

Пароль:

```text
guest
```
