# AutoAns WhatsApp Scan Service

Node.js microservice using `@whiskeysockets/baileys` for:
- QR scan login
- connection status
- sending WhatsApp messages
- automatic reconnect and watchdog restarts
- cPanel-friendly session persistence outside the app folder

## Setup

1. Install dependencies:
   - `npm install`
2. Copy env:
   - `copy .env.example .env` (Windows)
3. Update `.env` values:
   - `WHATSAPP_SCAN_API_KEY=4578jhfuhdj96586dkjiejkjdfiejk4582454`
   - `SESSION_BASE_DIR=/home/<cpanel-user>/autoans-whatsapp-session`
4. Start service:
   - `npm start`

## Endpoints

- `GET /health`
- `GET /heartbeat`
- `GET /status` (requires `x-api-key`)
- `GET /qr` (requires `x-api-key`)
- `POST /send` (requires `x-api-key`)
- `POST /logout` (requires `x-api-key`)
- `POST /restart` (requires `x-api-key`)

## Recovery Controls (.env)

- `LOGGED_OUT_GRACE_RETRIES=2`
- `STUCK_RESTART_AFTER_MS=180000`
- `WATCHDOG_INTERVAL_MS=30000`
- `CONFLICT_RECONNECT_DELAY_MS=15000`
- `NORMAL_RECONNECT_DELAY_MS=5000`
- `STARTUP_RECONNECT_DELAY_MS=7000`
- `PRESERVE_SESSION_ON_CONFLICT=true`
- `PRESERVE_SESSION_ON_LOGGED_OUT=true`

## Laravel Integration

Set in Laravel `.env`:

- `WHATSAPP_SCAN_BASE_URL=http://127.0.0.1:3001`
- `WHATSAPP_SCAN_API_KEY=4578jhfuhdj96586dkjiejkjdfiejk4582454`
- `WHATSAPP_SCAN_TIMEOUT=15`

Open Laravel page:

- `/whatsapp/scan`

## Recommended cPanel `.env`

Use values like this on cPanel:

```env
PORT=3001
TZ=Asia/Kolkata
WHATSAPP_SCAN_API_KEY=4578jhfuhdj96586dkjiejkjdfiejk4582454
DEFAULT_COUNTRY_CODE=91
SESSION_NAME=autoans-session
SESSION_BASE_DIR=/home/turnkeyi/autoans-whatsapp-session
LOGGED_OUT_GRACE_RETRIES=6
STUCK_RESTART_AFTER_MS=300000
WATCHDOG_INTERVAL_MS=20000
CONFLICT_RECONNECT_DELAY_MS=15000
NORMAL_RECONNECT_DELAY_MS=5000
STARTUP_RECONNECT_DELAY_MS=7000
PRESERVE_SESSION_ON_CONFLICT=true
PRESERVE_SESSION_ON_LOGGED_OUT=true
```

Create the session folder once in cPanel terminal:

```bash
mkdir -p /home/turnkeyi/autoans-whatsapp-session
chmod 700 /home/turnkeyi/autoans-whatsapp-session
```

## cPanel Keep-Alive (Important)

On many cPanel setups, Node app workers are recycled when idle. Add a cron job to keep the service warm:

- `*/1 * * * * curl -sS https://autoanswhatsapp.turnkeyinfotech.live/whatsapp/scan/heartbeat > /dev/null 2>&1`

If your Node app is exposed directly, prefer pinging its own health endpoint every minute:

- `*/1 * * * * curl -sS https://<your-node-domain>/health > /dev/null 2>&1`
