FROM node:22-slim AS build

WORKDIR /app

ARG VITE_API_KEY=credme-dev-local-key
ENV VITE_API_KEY=$VITE_API_KEY

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
