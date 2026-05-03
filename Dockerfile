FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip ca-certificates build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ml/requirements.txt ml/
RUN pip3 install --no-cache-dir --break-system-packages -r ml/requirements.txt

COPY web/package.json web/package-lock.json* web/
RUN cd web && npm install --omit=dev

COPY ml/ ml/
COPY web/ web/

ENV PORT=3000 \
    DATA_DIR=/app/data

EXPOSE 3000
CMD ["node", "web/server.js"]
