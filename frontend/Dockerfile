# Frontend Dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
# Copy only package manifest for dependency layer caching
COPY package.json ./
# No lockfile yet, use npm install (later switch back to npm ci after adding lockfile)
RUN npm install

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Allow overriding API base at build time
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
