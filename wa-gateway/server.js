const express = require('express');
const fs = require('fs');
const puppeteer = require('puppeteer');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

// Simple CORS middleware to allow requests from the frontend during development
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', process.env.CORS_ORIGINS || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const BACKEND_LOCAL_FALLBACK = 'http://localhost:8000';
let lastQr = null;

function resolveChromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    process.env.PUPPETEER_EXECUTABLE_PATH,
    puppeteer.executablePath(),
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      console.log('Using Chrome executable:', candidate);
      return candidate;
    }
  }

  const fallback = candidates[0];
  console.warn('No Chrome executable found from candidates. Falling back to:', fallback);
  return fallback;
}

const client = new Client({
  authStrategy: new LocalAuth(),
  puppeteer: {
    executablePath: resolveChromeExecutable(),
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('QR RECEIVED', qr);
  lastQr = qr;
});

client.on('ready', () => {
  console.log('WhatsApp client is ready');
  lastQr = null;
});

async function forwardToBackend(payload) {
  console.log('Forwarding message to backend', BACKEND_URL, 'payload:', payload);
  const start = Date.now();
  try {
    const response = await axios.post(`${BACKEND_URL}/whatsapp/webhook`, payload, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'X-WhatsApp-Gateway': '1',
      },
      timeout: 120000,
    });
    console.log('Backend reply received in', Date.now() - start, 'ms');
    return response;
  } catch (err) {
    const rawMessage = err?.message ?? err;
    const message = typeof rawMessage === 'string' ? rawMessage : JSON.stringify(rawMessage);
    console.warn('Backend request failed after', Date.now() - start, 'ms:', message);

    const isBackendDnsError = message.includes('ENOTFOUND backend') || message.includes('getaddrinfo ENOTFOUND backend') || err?.code === 'ENOTFOUND' || err?.code === 'EAI_AGAIN';
    if (isBackendDnsError) {
      console.warn('Backend hostname "backend" not resolvable; retrying with localhost fallback.');
      const fallbackStart = Date.now();
      const response = await axios.post(`${BACKEND_LOCAL_FALLBACK}/whatsapp/webhook`, payload, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
          'X-WhatsApp-Gateway': '1',
        },
        timeout: 120000,
      });
      console.log('Local fallback backend reply received in', Date.now() - fallbackStart, 'ms');
      return response;
    }

    throw err;
  }
}

client.on('message', async msg => {
  try {
    const from = msg.from;
    const body = msg.body;
    console.log('WhatsApp message event', {
      id: msg.id?._serialized,
      from,
      fromMe: msg.fromMe,
      hasMedia: msg.hasMedia,
      isStatus: msg.isStatus,
      type: msg.type,
      body,
    });

    if (!body) {
      console.log('Skipping non-text WhatsApp message', { from, type: msg.type });
      return;
    }

    console.log('WhatsApp message received from', from, 'body:', body);
    const response = await forwardToBackend(new URLSearchParams({ From: from, Body: body }).toString());

    let replyText = null;
    if (response && response.data) {
      if (typeof response.data === 'string') {
        const match = response.data.match(/<Message>([\s\S]*?)<\/Message>/);
        if (match) {
          replyText = match[1];
        } else {
          replyText = response.data.trim();
        }
      } else if (typeof response.data === 'object') {
        replyText = response.data.reply || response.data.response || response.data.text || null;
      }
    }

    if (replyText) {
      console.log('Backend reply for', from, ':', replyText);
      console.log('Sending reply to WhatsApp user', from);
      await client.sendMessage(from, replyText);
    } else {
      console.warn('No reply text returned from backend for message', from, 'backend response:', response?.data);
    }
  } catch (err) {
    console.error('Error forwarding message to backend', err?.message || err);
  }
});

client.initialize();

app.get('/qr', async (req, res) => {
  if (!lastQr) return res.json({ qr: null, ready: false });
  const dataUrl = await qrcode.toDataURL(lastQr);
  res.json({ qr: dataUrl, ready: false });
});

app.get('/status', (req, res) => {
  res.json({ ready: client.info?.pushname ? true : false, user: client.info?.pushname || null });
});

app.post('/send', async (req, res) => {
  const { to, body } = req.body;
  if (!to || !body) return res.status(400).json({ error: 'to and body required' });
  try {
    const message = await client.sendMessage(to, body);
    res.json({ id: message.id._serialized });
  } catch (err) {
    console.error('send error', err?.message || err);
    res.status(500).json({ error: 'failed to send' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`wa-gateway listening on ${PORT}`));
