FROM node:24-alpine AS build

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:24-alpine

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

EXPOSE 3000
# Docker подставляет HOSTNAME = имя контейнера, и standalone-сервер слушает его.
# 0.0.0.0 нужен, чтобы запрос доходил и от nginx, и от healthcheck.
CMD ["sh", "-c", "HOSTNAME=0.0.0.0 exec node server.js"]
