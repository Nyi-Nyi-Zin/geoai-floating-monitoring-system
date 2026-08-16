FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    postgresql-client libpq5 libgeos-c1v5 gdal-bin \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN python3 -m pip install --no-cache-dir fastapi uvicorn \
    && npm install -g corepack@latest \
    && corepack enable \
    && corepack pnpm install \
    && corepack pnpm run build

ENV NODE_ENV=production
CMD ["node", "dist/index.js"]
