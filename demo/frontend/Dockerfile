# Front démo AbidjanMob — build Vite puis service statique nginx.
# Les tuiles carto sont servies via le montage ./demo/frontend/public/tiles
# (docker-compose) ; le service tiles-init les récupère si absentes.
FROM node:22-alpine AS build
WORKDIR /src

COPY demo/frontend/package.json demo/frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY demo/frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY demo/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
