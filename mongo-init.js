db = db.getSiblingDB("social_network_mongo");

db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["login", "email", "password", "first_name", "last_name", "created_at"],
      properties: {
        login: {
          bsonType: "string",
          pattern: "^[a-zA-Z0-9_]{3,30}$"
        },
        email: {
          bsonType: "string",
          pattern: "^.+@.+\\..+$"
        },
        password: {
          bsonType: "string",
          minLength: 6
        },
        first_name: {
          bsonType: "string"
        },
        last_name: {
          bsonType: "string"
        },
        age: {
          bsonType: "int",
          minimum: 0,
          maximum: 120
        },
        interests: {
          bsonType: "array",
          items: {
            bsonType: "string"
          }
        },
        created_at: {
          bsonType: "date"
        }
      }
    }
  }
});

db.createCollection("posts");
db.createCollection("messages");

db.users.insertMany([
  { login: "alice", email: "alice@example.com", password: "123456", first_name: "Alice", last_name: "Smith", age: 21, interests: ["ml", "design"], created_at: new Date() },
  { login: "bob", email: "bob@example.com", password: "123456", first_name: "Bob", last_name: "Johnson", age: 24, interests: ["backend", "docker"], created_at: new Date() },
  { login: "carol", email: "carol@example.com", password: "123456", first_name: "Carol", last_name: "Brown", age: 22, interests: ["frontend", "react"], created_at: new Date() },
  { login: "dave", email: "dave@example.com", password: "123456", first_name: "Dave", last_name: "White", age: 27, interests: ["devops"], created_at: new Date() },
  { login: "eva", email: "eva@example.com", password: "123456", first_name: "Eva", last_name: "Black", age: 20, interests: ["ui", "figma"], created_at: new Date() },
  { login: "frank", email: "frank@example.com", password: "123456", first_name: "Frank", last_name: "Green", age: 30, interests: ["postgres", "mongodb"], created_at: new Date() },
  { login: "grace", email: "grace@example.com", password: "123456", first_name: "Grace", last_name: "Hall", age: 19, interests: ["math", "algorithms"], created_at: new Date() },
  { login: "henry", email: "henry@example.com", password: "123456", first_name: "Henry", last_name: "King", age: 25, interests: ["cpp", "userver"], created_at: new Date() },
  { login: "irene", email: "irene@example.com", password: "123456", first_name: "Irene", last_name: "Moore", age: 23, interests: ["python", "fastapi"], created_at: new Date() },
  { login: "jack", email: "jack@example.com", password: "123456", first_name: "Jack", last_name: "Lee", age: 28, interests: ["systems", "architecture"], created_at: new Date() }
]);

const users = db.users.find().toArray();

db.posts.insertMany([
  { author_id: users[0]._id, content: "First post by Alice", tags: ["intro", "ml"], likes: [users[1]._id], comments: [{ user_id: users[1]._id, text: "Nice post", created_at: new Date() }], created_at: new Date() },
  { author_id: users[1]._id, content: "First post by Bob", tags: ["backend"], likes: [users[0]._id], comments: [], created_at: new Date() },
  { author_id: users[2]._id, content: "Carol writes about React", tags: ["frontend", "react"], likes: [], comments: [], created_at: new Date() },
  { author_id: users[3]._id, content: "Docker compose is useful", tags: ["docker", "devops"], likes: [users[4]._id], comments: [], created_at: new Date() },
  { author_id: users[4]._id, content: "UI design matters", tags: ["design"], likes: [users[0]._id], comments: [], created_at: new Date() },
  { author_id: users[5]._id, content: "MongoDB document model", tags: ["mongodb", "database"], likes: [], comments: [], created_at: new Date() },
  { author_id: users[6]._id, content: "Algorithms are beautiful", tags: ["math"], likes: [users[7]._id], comments: [], created_at: new Date() },
  { author_id: users[7]._id, content: "C++ backend with userver", tags: ["cpp", "backend"], likes: [users[1]._id], comments: [], created_at: new Date() },
  { author_id: users[8]._id, content: "FastAPI is simple", tags: ["python", "api"], likes: [], comments: [], created_at: new Date() },
  { author_id: users[9]._id, content: "Architecture first", tags: ["architecture"], likes: [users[0]._id, users[1]._id], comments: [], created_at: new Date() }
]);

db.messages.insertMany([
  { from_user_id: users[0]._id, to_user_id: users[1]._id, text: "Hi Bob", is_read: false, created_at: new Date() },
  { from_user_id: users[1]._id, to_user_id: users[0]._id, text: "Hi Alice", is_read: true, created_at: new Date() },
  { from_user_id: users[2]._id, to_user_id: users[3]._id, text: "Hello Dave", is_read: false, created_at: new Date() },
  { from_user_id: users[3]._id, to_user_id: users[2]._id, text: "Hello Carol", is_read: true, created_at: new Date() },
  { from_user_id: users[4]._id, to_user_id: users[5]._id, text: "MongoDB task?", is_read: false, created_at: new Date() },
  { from_user_id: users[5]._id, to_user_id: users[4]._id, text: "Yes, document model", is_read: true, created_at: new Date() },
  { from_user_id: users[6]._id, to_user_id: users[7]._id, text: "Let's solve algorithms", is_read: false, created_at: new Date() },
  { from_user_id: users[7]._id, to_user_id: users[6]._id, text: "Sure", is_read: true, created_at: new Date() },
  { from_user_id: users[8]._id, to_user_id: users[9]._id, text: "FastAPI or userver?", is_read: false, created_at: new Date() },
  { from_user_id: users[9]._id, to_user_id: users[8]._id, text: "Both are useful", is_read: true, created_at: new Date() }
]);

db.users.createIndex({ login: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });
db.posts.createIndex({ author_id: 1 });
db.messages.createIndex({ from_user_id: 1 });
db.messages.createIndex({ to_user_id: 1 });