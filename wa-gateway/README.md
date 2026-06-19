wa-gateway

Self-hosted WhatsApp Web gateway using whatsapp-web.js.

Endpoints:
- GET /qr -> returns JSON { qr: <dataUrl> } (scan this QR with WhatsApp mobile app)
- GET /status -> { ready: boolean }
- POST /send { to, body } -> send message

Environment variables:
- BACKEND_URL (default: http://backend:8000)
- PORT (default: 3001)

Usage:
- Run the container and visit /qr to scan the QR code with WhatsApp mobile app.
- Once connected, incoming messages will be POSTed to your backend /whatsapp/webhook endpoint.
