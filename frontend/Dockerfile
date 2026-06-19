FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY tsconfig.json ./
COPY postcss.config.js ./
COPY tailwind.config.js ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
