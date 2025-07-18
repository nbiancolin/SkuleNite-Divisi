FROM node:20 as build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM nginx:latest
COPY --from=build /app/dist /usr/share/nginx/html
