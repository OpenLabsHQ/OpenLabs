FROM oven/bun:1.1 AS builder

WORKDIR /app

COPY . .

RUN bun install
RUN bun run build:prod

FROM oven/bun:1.1-slim

WORKDIR /app

COPY --from=builder /app/build ./build
COPY --from=builder /app/static ./static
COPY --from=builder /app/proxy.js ./proxy.js
COPY --from=builder /app/package.json ./package.json

RUN bun install --production

EXPOSE 3000
EXPOSE 3001

ENV NODE_ENV=production

CMD ["bun", "./build/index.js"]
