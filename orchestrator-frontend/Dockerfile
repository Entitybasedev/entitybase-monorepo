FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_APP_VERSION
ENV VITE_APP_VERSION=$VITE_APP_VERSION
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 8083
CMD ["npx", "serve", "-s", "dist", "-l", "8083"]
