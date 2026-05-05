import os
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient


MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "social_network_mongo")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

app = FastAPI(title="Social Network MongoDB API")


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


class UserCreate(BaseModel):
    login: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    age: Optional[int] = None
    interests: list[str] = []


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    interests: Optional[list[str]] = None


class PostCreate(BaseModel):
    author_id: str
    content: str
    tags: list[str] = []


class MessageCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    text: str


@app.get("/users")
def get_users(login: Optional[str] = None, min_age: Optional[int] = None):
    query = {}

    if login:
        query["login"] = {"$eq": login}

    if min_age is not None:
        query["age"] = {"$gt": min_age}

    users = list(db.users.find(query))
    return [to_json(user) for user in users]


@app.post("/users")
def create_user(user: UserCreate):
    doc = user.model_dump()
    doc["created_at"] = datetime.utcnow()

    try:
        result = db.users.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    created = db.users.find_one({"_id": result.inserted_id})
    return to_json(created)


@app.patch("/users/{user_id}")
def update_user(user_id: str, data: UserUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.users.update_one(
        {"_id": oid(user_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.users.find_one({"_id": oid(user_id)})
    return to_json(user)


@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    result = db.users.delete_one({"_id": oid(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "deleted"}


@app.get("/posts")
def get_posts(author_id: Optional[str] = None, tag: Optional[str] = None):
    query = {}

    if author_id:
        query["author_id"] = oid(author_id)

    if tag:
        query["tags"] = {"$in": [tag]}

    posts = list(db.posts.find(query).sort("created_at", -1))
    return [to_json(post) for post in posts]


@app.post("/posts")
def create_post(post: PostCreate):
    author = db.users.find_one({"_id": oid(post.author_id)})

    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    doc = {
        "author_id": oid(post.author_id),
        "content": post.content,
        "tags": post.tags,
        "likes": [],
        "comments": [],
        "created_at": datetime.utcnow()
    }

    result = db.posts.insert_one(doc)
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
def create_message(message: MessageCreate):
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
    created = db.messages.find_one({"_id": result.inserted_id})
    return to_json(created)


@app.patch("/messages/{message_id}/read")
def mark_message_as_read(message_id: str):
    result = db.messages.update_one(
        {"_id": oid(message_id)},
        {"$set": {"is_read": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    message = db.messages.find_one({"_id": oid(message_id)})
    return to_json(message)


@app.delete("/messages/{message_id}")
def delete_message(message_id: str):
    result = db.messages.delete_one({"_id": oid(message_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"status": "deleted"}


@app.get("/stats/posts-by-users")
def posts_by_users():
    pipeline = [
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
        {"$unwind": "$author"},
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

    return list(db.posts.aggregate(pipeline))