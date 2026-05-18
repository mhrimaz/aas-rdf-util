FROM cgr.dev/chainguard/node:latest AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM cgr.dev/chainguard/nginx:latest
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
