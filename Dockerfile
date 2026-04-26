FROM node:22-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat python3 make g++
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Install Python ML dependencies
FROM python:3.13-alpine AS ml-deps
RUN pip install uv
WORKDIR /app/ml
COPY ml/pyproject.toml ml/uv.lock ./
RUN uv sync --frozen --no-dev

# Build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN mkdir -p data
RUN npm run build

# Production — node base with python added
FROM base AS runner
RUN apk add --no-cache python3
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy ML pipeline + Python venv
COPY --from=ml-deps /app/ml/.venv ./ml/.venv
COPY ml/parser ./ml/parser
COPY ml/eval ./ml/eval
COPY ml/optimize/compiled_program.json ./ml/optimize/compiled_program.json
COPY ml/pyproject.toml ./ml/pyproject.toml

# Create data directory for SQLite
RUN mkdir -p /app/data && chown nextjs:nodejs /app/data

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV ML_DIR=/app/ml

CMD ["node", "server.js"]
