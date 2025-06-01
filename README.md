# Ecological Journey

🥋 *Train, Track, and Transcend* – A platform for martial artists to annotate, organize, and reflect on their journey with partners, clips, and insights.

## Features

- 🎥 **Video Archive**: Organize training footage by playlist, model, and partner.
- ✂️ **Clip Manager**: Annotate key moments and tag techniques.
- 🧠 **Technique Tracker**: Track progress over time on specific techniques.
- 👥 **Partner Journals**: View training logs and feedback across partners.
- 🔎 **Search & Filter**: Slice across metadata like playlist, model, or time period.
- 🌱 **Self-Hosted & Lightweight**: Runs with FastAPI + NiceGUI.

## Demo

👉 [Live Demo](https://ecological-journey.onrender.com)

## 🔄 Lazy Login Flow (Render-Friendly)

- Backend sleeps on free Render plan
- Login triggers backend to wake
- UI displays:
  > “Waking up servers… Please wait.”

This avoids failed login attempts and improves user clarity.

---

## Local Setup

```bash
git clone https://github.com/jshreyas/ecological_journey.git
cd ecological_journey
cp .env.example .env  # configure backend and redis URLs

# Start services
docker-compose up --build
```

## Production Deployment (Render + Upstash)

- UI and API hosted on Render (free tier)
- Caching via Upstash Redis
- MongoDB via Atlas
- Lazy-login pattern with "Waking up server..." UX for cold start

---

## License

This project is licensed under the [MIT License](./LICENSE).

---

🧠 See `docs/architecture.md` for more.
