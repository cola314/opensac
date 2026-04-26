FROM node:22-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat python3 make g++
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV DATABASE_URL=./data/opensac.db
RUN mkdir -p data
RUN node -e "\
const Database = require('better-sqlite3');\
const db = new Database('./data/opensac.db');\
db.pragma('journal_mode = WAL');\
db.exec('CREATE TABLE IF NOT EXISTS concerts (id INTEGER PRIMARY KEY AUTOINCREMENT, sn TEXT UNIQUE NOT NULL, title TEXT NOT NULL, title_eng TEXT, begin_date TEXT NOT NULL, end_date TEXT, playtime TEXT, place_name TEXT, place_code TEXT, price_info TEXT, sale_state TEXT, detail_text TEXT, start_week TEXT, sac_url TEXT, crawled_at TEXT NOT NULL, programs_text TEXT DEFAULT \"\")');\
db.exec('CREATE VIRTUAL TABLE IF NOT EXISTS concerts_fts USING fts5(title, detail_text, programs_text, content=concerts, content_rowid=id)');\
db.exec('CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY AUTOINCREMENT, concert_sn TEXT NOT NULL, composer TEXT NOT NULL, piece TEXT NOT NULL, created_at TEXT NOT NULL)');\
db.close();\
console.log('DB initialized');"
RUN npm run build

# Production
FROM base AS runner
RUN apk add --no-cache python3 py3-pip
# Install ML Python dependencies globally
RUN pip3 install --break-system-packages dspy-ai tqdm litellm
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy ML pipeline code (no venv needed, packages installed globally)
COPY ml/parser ./ml/parser
COPY ml/eval ./ml/eval
COPY ml/optimize/compiled_program.json ./ml/optimize/compiled_program.json

# Create data directory for SQLite
RUN mkdir -p /app/data && chown nextjs:nodejs /app/data

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV ML_DIR=/app/ml

CMD ["node", "server.js"]
