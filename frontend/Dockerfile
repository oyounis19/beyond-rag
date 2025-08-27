# Frontend Dockerfile
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies (no lockfile yet). Once a lockfile is committed, switch to: COPY package*.json ./ && npm ci
COPY package.json ./
RUN npm install

# Copy application source
COPY . .

# Allow overriding API base at build time
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
