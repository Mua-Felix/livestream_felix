# 🎥 LiveStream Felix
### Professional Video Conferencing Platform — Built with Django + WebRTC

---

## ✨ Features

| Category | Features |
|----------|----------|
| **Video Conferencing** | HD WebRTC video, up to 100 participants, adaptive grid layout (1/2/4/6/9/16 tiles) |
| **Audio** | Real-time mic toggle, mute on entry, host force-mute, audio level meter |
| **Screen Sharing** | Full screen / tab / window sharing, remote screen share indicator |
| **Chat** | Real-time WebSocket chat, emoji picker, typing indicators, message history, pinning, reply-to |
| **Reactions** | Live emoji reactions floating on video tiles (👍 👏 ❤️ 😂 😮 🎉 🔥 ✋) |
| **Host Controls** | Mute all, mute individual, kick participants, end meeting for all |
| **Polls** | Create & launch live polls, attendees vote in real time |
| **Raise Hand** | Participants signal the host via hand raise notification |
| **Meeting Types** | Instant, Scheduled, Personal Room, Webinar |
| **Security** | Password-protected rooms, waiting room, host approval |
| **Dashboard** | Stats cards, upcoming/recent meetings, online users, quick join |
| **Settings** | Camera/mic device picker, background blur toggle, meeting code copy |
| **Profile** | Avatar upload, bio, job title, organization, stats |
| **Deployment** | Railway-ready with Daphne ASGI server |

---

## 🚀 Quick Start (Local)

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd livestream_felix
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 3. Start the Server

```bash
# Development (uses Django's dev server with channels)
python manage.py runserver

# Or with Daphne (recommended):
daphne -b 127.0.0.1 -p 8000 livestream_felix.asgi:application
```

### 4. Open Your Browser

```
http://localhost:8000
```

---

## 🏗️ Project Structure

```
livestream_felix/
├── livestream_felix/        # Django project config
│   ├── settings.py          # All settings
│   ├── urls.py              # Root URL routing
│   ├── asgi.py              # ASGI + WebSocket routing
│   └── wsgi.py
│
├── accounts/                # User auth & profiles
│   ├── models.py            # Custom User model (UUID pk)
│   ├── views.py             # Register / Login / Profile
│   └── forms.py
│
├── rooms/                   # Video meeting rooms
│   ├── models.py            # Room, Participant, Reaction, Whiteboard
│   ├── consumers.py         # WebRTC signaling WebSocket consumer
│   ├── views.py             # Room CRUD + instant meeting
│   └── routing.py           # ws/room/<code>/
│
├── chat/                    # Real-time messaging
│   ├── models.py            # Message, DirectMessage
│   ├── consumers.py         # Chat WebSocket consumer
│   └── routing.py           # ws/chat/<code>/
│
├── dashboard/               # Main dashboard
│   └── views.py             # Home, Meetings list, People
│
├── templates/               # All HTML templates
│   ├── base.html            # Full design system + sidebar
│   ├── accounts/            # Login, Register, Profile
│   ├── rooms/               # Room UI, Join, Create
│   └── dashboard/           # Home, Meetings, People
│
├── static/                  # CSS, JS, Images
├── requirements.txt
├── Procfile                 # Railway process definition
├── railway.json             # Railway config
└── nixpacks.toml            # Build instructions
```

---

## 🌐 Deploying to Railway

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "LiveStream Felix - Initial release"
git remote add origin https://github.com/yourusername/livestream-felix.git
git push -u origin main
```

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo** → select your repo
3. Railway auto-detects the `nixpacks.toml` and `Procfile`

### Step 3: Add Environment Variables

In your Railway service settings → **Variables**, add:

```
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=*.railway.app,your-custom-domain.com
DATABASE_URL=<auto-filled by Railway Postgres plugin>
```

### Step 4: Add PostgreSQL (optional but recommended)

In Railway dashboard → **+ New** → **Database** → **PostgreSQL**  
Railway auto-injects `DATABASE_URL`. Update `settings.py`:

```python
import environ
env = environ.Env()
DATABASES = {'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')}
```

### Step 5: Add Redis for Channel Layers (for multi-server WebSockets)

1. Railway → **+ New** → **Redis**
2. Add to env: `REDIS_URL=<auto-injected>`
3. Update `settings.py`:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [env('REDIS_URL')]},
    }
}
```

### Step 6: Custom Domain

Railway → **Settings** → **Domains** → Add your domain.

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 |
| Real-time | Django Channels 4 (WebSocket) |
| Video | WebRTC (getUserMedia, RTCPeerConnection) |
| ASGI Server | Daphne |
| Channel Layer | In-Memory (dev) / Redis (production) |
| Database | SQLite (dev) / PostgreSQL (production) |
| Styling | Custom CSS design system (no frameworks) |
| Icons | Font Awesome 6 |
| Fonts | Inter + Space Grotesk (Google Fonts) |
| Deployment | Railway |

---

## 🎨 Design System

LiveStream Felix uses a custom dark design system with:
- **Colors**: Deep Navy (`#080c14`) + Electric Indigo (`#5b6ef5`) + Cyan (`#00d4ff`)
- **Typography**: Space Grotesk (headings) + Inter (body)
- **Components**: Cards, Stat tiles, Status badges, Control buttons, Video tiles
- **Responsive**: Full mobile support with collapsible sidebar

---

## 📋 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | `True` for dev, `False` for prod |
| `ALLOWED_HOSTS` | ✅ | Comma-separated allowed domains |
| `DATABASE_URL` | ➖ | PostgreSQL URL (falls back to SQLite) |
| `REDIS_URL` | ➖ | Redis URL for channel layers |
| `METERED_API_KEY` | ➖ | Metered.ca TURN server API key |

---

## 🔐 Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Use PostgreSQL (not SQLite)
- [ ] Add Redis for WebSocket channel layers
- [ ] Add HTTPS/TLS (required for camera/mic in browsers)
- [ ] Set up TURN server for NAT traversal (Metered, Twilio, or Coturn)
- [ ] Run `collectstatic` for static files

---

## 🤝 TURN Server Setup (for production video calls)

WebRTC needs TURN servers when users are behind strict firewalls or NAT.
Use [Metered.ca](https://metered.ca) (free tier available):

1. Sign up → get API key
2. Update `settings.py`:
```python
METERED_API_KEY = env('METERED_API_KEY', default='')
```
3. Update the ICE config in `room.html`:
```javascript
const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.metered.ca:80' },
    { urls: 'turn:global.relay.metered.ca:80', username: '...', credential: '...' },
  ]
};
```

---

Built with ❤️ by **Felix** | Powered by Django + WebRTC
