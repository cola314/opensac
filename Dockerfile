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
RUN mkdir -p data && touch data/opensac.db
ENV DATABASE_URL=./data/opensac.db
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
