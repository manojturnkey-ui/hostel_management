FROM node:20-bookworm-slim

ENV NODE_ENV=production
ENV PORT=10000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    dumb-init \
  && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install --omit=dev

COPY . .

EXPOSE 10000

CMD ["dumb-init", "node", "index.js"]
