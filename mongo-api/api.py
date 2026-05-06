import json
import os
import time
from datetime import datetime
from typing import Optional

import redis
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient


MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "social_network_mongo")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="Social Network MongoDB API")


CACHE_TTL = 60
RATE_LIMIT = 10
RATE_WINDOW = 60


def oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid ObjectId")
    return ObjectId(value)


def to_json(doc):
    doc["_id"] = str(doc["_id"])

    for key in ["author_id", "from_user_id", "to_user_id", "user_id"]:
        if key in doc and isinstance(doc[key], ObjectId):
            doc[key] = str(doc[key])

    if "likes" in doc:
        doc["likes"] = [str(x) for x in doc["likes"]]

    if "comments" in doc:
        for comment in doc["comments"]:
            if "user_id" in comment and isinstance(comment["user_id"], ObjectId):
                comment["user_id"] = str(comment["user_id"])

    return doc


def cache_get(key: str):
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception:
        return None
    return None


def cache_set(key: str, value, ttl: int = CACHE_TTL):
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete_prefix(prefix: str):
    try:
        for key in redis_client.scan_iter(f"{prefix}*"):
            redis_client.delete(key)
    except Exception:
        pass


def invalidate_users_cache():
    cache_delete_prefix("users:")


def invalidate_posts_cache():
    cache_delete_prefix("posts:")
    cache_delete_prefix("stats:")


def invalidate_messages_cache():
    cache_delete_prefix("messages:")


def check_rate_limit(request: Request, response: Response, key_prefix: str):
    client_ip = request.client.host if request.client else "unknown"
    window = int(time.time() // RATE_WINDOW)
    key = f"rate_limit:{key_prefix}:{client_ip}:{window}"

    current = redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, RATE_WINDOW)

    remaining = max(RATE_LIMIT - current, 0)
    reset = (window + 1) * RATE_WINDOW

    headers = {
        "X-RateLimit-Limit": str(RATE_LIMIT),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset),
    }

    response.headers["X-RateLimit-Limit"] = headers["X-RateLimit-Limit"]
    response.headers["X-RateLimit-Remaining"] = headers["X-RateLimit-Remaining"]
    response.headers["X-RateLimit-Reset"] = headers["X-RateLimit-Reset"]

    if current > RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers=headers
        )


class UserCreate(BaseModel):
    login: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    age: Optional[int] = None
    interests: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    interests: Optional[list[str]] = None


class PostCreate(BaseModel):
    author_id: str
    content: str
    tags: list[str] = Field(default_factory=list)


class MessageCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    text: str


@app.get("/users")
def get_users(response: Response, login: Optional[str] = None, min_age: Optional[int] = None):
    cache_key = f"users:login={login}:min_age={min_age}"
    cached = cache_get(cache_key)

    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    query = {}

    if login:
        query["login"] = {"$eq": login}

    if min_age is not None:
        query["age"] = {"$gt": min_age}

    users = [to_json(user) for user in db.users.find(query)]

    cache_set(cache_key, users)
    response.headers["X-Cache"] = "MISS"

    return users


@app.post("/users")
def create_user(user: UserCreate):
    doc = user.model_dump()
    doc["created_at"] = datetime.utcnow()

    try:
        result = db.users.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    invalidate_users_cache()

    created = db.users.find_one({"_id": result.inserted_id})
    return to_json(created)


@app.patch("/users/{user_id}")
def update_user(user_id: str, data: UserUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    user_object_id = oid(user_id)

    result = db.users.update_one(
        {"_id": user_object_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    invalidate_users_cache()
    invalidate_posts_cache()
    invalidate_messages_cache()

    user = db.users.find_one({"_id": user_object_id})
    return to_json(user)


@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    result = db.users.delete_one({"_id": oid(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    invalidate_users_cache()
    invalidate_posts_cache()
    invalidate_messages_cache()

    return {"status": "deleted"}


@app.get("/posts")
def get_posts(response: Response, author_id: Optional[str] = None, tag: Optional[str] = None):
    cache_key = f"posts:author_id={author_id}:tag={tag}"
    cached = cache_get(cache_key)

    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    query = {}

    if author_id:
        query["author_id"] = oid(author_id)

    if tag:
        query["tags"] = {"$in": [tag]}

    posts = [to_json(post) for post in db.posts.find(query).sort("created_at", -1)]

    cache_set(cache_key, posts)
    response.headers["X-Cache"] = "MISS"

    return posts


@app.post("/posts")
def create_post(post: PostCreate):
    author_object_id = oid(post.author_id)
    author = db.users.find_one({"_id": author_object_id})

    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    doc = {
        "author_id": author_object_id,
        "content": post.content,
        "tags": post.tags,
        "likes": [],
        "comments": [],
        "created_at": datetime.utcnow()
    }

    result = db.posts.insert_one(doc)

    invalidate_posts_cache()

    created = db.posts.find_one({"_id": result.inserted_id})
    return to_json(created)


@app.post("/posts/{post_id}/likes/{user_id}")
def like_post(post_id: str, user_id: str):
    result = db.posts.update_one(
        {"_id": oid(post_id)},
        {"$addToSet": {"likes": oid(user_id)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")

    invalidate_posts_cache()

    post = db.posts.find_one({"_id": oid(post_id)})
    return to_json(post)


@app.delete("/posts/{post_id}/likes/{user_id}")
def unlike_post(post_id: str, user_id: str):
    result = db.posts.update_one(
        {"_id": oid(post_id)},
        {"$pull": {"likes": oid(user_id)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")

    invalidate_posts_cache()

    post = db.posts.find_one({"_id": oid(post_id)})
    return to_json(post)


@app.post("/posts/{post_id}/comments")
def add_comment(post_id: str, user_id: str, text: str):
    comment = {
        "user_id": oid(user_id),
        "text": text,
        "created_at": datetime.utcnow()
    }

    result = db.posts.update_one(
        {"_id": oid(post_id)},
        {"$push": {"comments": comment}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")

    invalidate_posts_cache()

    post = db.posts.find_one({"_id": oid(post_id)})
    return to_json(post)


@app.get("/messages")
def get_messages(user_id: str):
    user_oid = oid(user_id)

    query = {
        "$or": [
            {"from_user_id": user_oid},
            {"to_user_id": user_oid}
        ]
    }

    messages = list(db.messages.find(query).sort("created_at", -1))
    return [to_json(message) for message in messages]


@app.post("/messages")
def create_message(message: MessageCreate, request: Request, response: Response):
    check_rate_limit(request, response, "create_message")

    from_id = oid(message.from_user_id)
    to_id = oid(message.to_user_id)

    if not db.users.find_one({"_id": from_id}):
        raise HTTPException(status_code=404, detail="Sender not found")

    if not db.users.find_one({"_id": to_id}):
        raise HTTPException(status_code=404, detail="Receiver not found")

    doc = {
        "from_user_id": from_id,
        "to_user_id": to_id,
        "text": message.text,
        "is_read": False,
        "created_at": datetime.utcnow()
    }

    result = db.messages.insert_one(doc)

    invalidate_messages_cache()

    created = db.messages.find_one({"_id": result.inserted_id})
    return to_json(created)


@app.patch("/messages/{message_id}/read")
def mark_message_as_read(message_id: str):
    message_object_id = oid(message_id)

    result = db.messages.update_one(
        {"_id": message_object_id},
        {"$set": {"is_read": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    invalidate_messages_cache()

    message = db.messages.find_one({"_id": message_object_id})
    return to_json(message)


@app.delete("/messages/{message_id}")
def delete_message(message_id: str):
    result = db.messages.delete_one({"_id": oid(message_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    invalidate_messages_cache()

    return {"status": "deleted"}


@app.get("/stats/posts-by-users")
def posts_by_users(response: Response):
    cache_key = "stats:posts-by-users"
    cached = cache_get(cache_key)

    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    pipeline = [
        {
            "$match": {
                "content": {"$ne": ""}
            }
        },
        {
            "$group": {
                "_id": "$author_id",
                "posts_count": {"$sum": 1},
                "likes_count": {"$sum": {"$size": "$likes"}}
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        {
            "$unwind": "$author"
        },
        {
            "$project": {
                "_id": 0,
                "user_id": {"$toString": "$_id"},
                "login": "$author.login",
                "posts_count": 1,
                "likes_count": 1
            }
        },
        {
            "$sort": {
                "posts_count": -1,
                "likes_count": -1
            }
        }
    ]

    result = list(db.posts.aggregate(pipeline))

    cache_set(cache_key, result)
    response.headers["X-Cache"] = "MISS"

    return result