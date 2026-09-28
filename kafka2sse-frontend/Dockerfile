FROM node:22-alpine AS build
WORKDIR /app
ARG KAFKA2SSE_BACKEND_URL
ARG VITE_APP_VERSION
ENV KAFKA2SSE_BACKEND_URL=$KAFKA2SSE_BACKEND_URL
ENV VITE_APP_VERSION=$VITE_APP_VERSION
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
RUN apk add --no-cache wget
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 8889
CMD ["serve", "-s", "dist", "-l", "8889"]
