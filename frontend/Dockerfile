FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

FROM nginx:alpine
# Defaults for local/compose use; override via environment on the platform.
# nginx's entrypoint substitutes these into /etc/nginx/conf.d at startup.
ENV PORT=80 \
    BACKEND_HOST=backend \
    BACKEND_PORT=8000
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
