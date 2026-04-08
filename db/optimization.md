# Оптимизация запросов

## Цель

Цель — ускорить основные запросы системы за счёт индексов и уменьшения количества полных сканирований таблиц.

Часто используемые операции:
- получение постов пользователя;
- получение сообщений чата;
- получение чатов пользователя;
- получение друзей;
- проверка активных сессий.


## Добавленные индексы

### По внешним ключам
Используются для ускорения JOIN:

- posts(author_id)
- chat_members(user_id)
- messages(chat_id)
- messages(sender_id)
- friendships(user_id, friend_id)
- sessions(user_id)

### Для WHERE

- idx_posts_author_id
- idx_messages_chat_id
- idx_friendships_status
- idx_sessions_expires_at

### Составные индексы

Для фильтрации + сортировки:

- idx_posts_author_id_created_at
- idx_messages_chat_id_created_at
- idx_friendships_user_id_status
- idx_sessions_user_id_expires_at

## Примеры оптимизации

### Сообщения чата

```sql
EXPLAIN
SELECT *
FROM messages
WHERE chat_id = 1
ORDER BY created_at DESC;
```

До добавления индекса:
- Seq Scan
- Sort

После добавления индекса:

```sql
CREATE INDEX idx_messages_chat_id_created_at
ON messages(chat_id, created_at DESC);
```

Используется:
- Index Scan
- сортировка не требуется отдельно


Посты пользователя
```sql
EXPLAIN
SELECT *
FROM posts
WHERE author_id = 1
ORDER BY created_at DESC;
```
До:
- Seq Scan
- Sort

После добавления индекса:
```sql
CREATE INDEX idx_posts_author_id_created_at
ON posts(author_id, created_at DESC);
```
Используется:
- Index Scan

Чаты пользователя
```sql
SELECT c.*
FROM chats c
JOIN chat_members cm ON cm.chat_id = c.id
WHERE cm.user_id = 1;
```
Проблема:
- полный перебор chat_members

Решение:
``` sql
CREATE INDEX idx_chat_members_user_id
ON chat_members(user_id);
```
Результат:
- быстрее выполняется JOIN

Друзья
```sql
SELECT *
FROM friendships
WHERE user_id = 1 AND status = 'accepted';
```
Решение:
```sql
CREATE INDEX idx_friendships_user_id_status
ON friendships(user_id, status);
```

Сессии
```sql
SELECT *
FROM sessions
WHERE user_id = 1 AND expires_at > NOW();
```
Решение:
```sql
CREATE INDEX idx_sessions_user_id_expires_at
ON sessions(user_id, expires_at);
```

## Итог

После добавления индексов:
- уменьшилось количество Seq Scan;
- ускорились JOIN;
- быстрее работают WHERE и ORDER BY;
- снизилась нагрузка на БД.

**Партиционирование:**

Таблица messages будет самой большой.

Можно разбить её по дате (created_at), например по месяцам:
- messages_2025_01
- messages_2025_02

Это ускорит выборки и упростит работу с большим объёмом данных.
