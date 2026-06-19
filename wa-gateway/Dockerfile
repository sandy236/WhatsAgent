FROM node:20-bullseye-slim
WORKDIR /app

# Install dependencies required by whatsapp-web.js / puppeteer
RUN apt-get update && apt-get install -y \
    wget ca-certificates fonts-liberation libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libgbm1 libgtk-3-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

COPY wa-gateway/package.json ./
RUN npm install --production
COPY wa-gateway/server.js ./

# Persist session data for LocalAuth
VOLUME ["/app/session"]
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
EXPOSE 3001
CMD ["node", "server.js"]
