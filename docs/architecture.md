# System Architecture

This document outlines the architecture for the Ecological Journey platform, both for local development and production.

---

## 🧱 Services Overview

### UI (`NiceGUI`)

- Written in Python with [NiceGUI](https://nicegui.io)
- Hosts all frontend routes and pages
- Talks to backend via FastAPI endpoints
- Communicates with Redis for caching layer
- Handles login, annotation, clip creation, etc.
- Handles all core business logic

### API (`FastAPI`)

- Handles all data logic
- Connects to MongoDB for data persistence

### Redis (Caching Layer)

- Used to cache video/clip metadata to reduce backend load
- Writes are persisted to backend when it comes online
- In production: [Upstash Redis](https://upstash.com/)
- In dev: Docker container

### MongoDB

- Stores users, videos, clips, playlists, tags, etc.
- Atlas hosted in prod
- In dev: Docker container

---

## 🔗 Interfaces Between Services

| Service A    | Talks to | Protocol | Purpose                             |
| ------------ | -------- | -------- | ----------------------------------- |
| UI (NiceGUI) | API      | HTTP     | User login, fetch videos, tag clips |
| UI (NiceGUI) | Redis    | Redis-Py | Read metadata for fast UI loads     |
| API          | MongoDB  | PyMongo  | Store/fetch user and clip data      |

---

## ⚙️ MVP Local Setup

```
docker-compose up --build
```

Services:

- `nicegui:8000`
- `fastapi:8001`
- `mongodb:27017`
- `redis:6379`

---

## ☁️ Production Setup

- **Render**: UI + API with free tier
- **Upstash Redis**: Free caching layer with long TTL
- **MongoDB Atlas**: free DB

Cold start on Render handled with lazy-login UX.

---

## MVP Architecture Diagram

```
[user] --> NiceGUI --> Redis ⟷ FastAPI --> MongoDB
                        ↑       |
                fallback if     |
                cache miss     ⬇
                         writes persist
```
