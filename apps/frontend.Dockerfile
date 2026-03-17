FROM node:20

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .

CMD ["npm", "run", "dev"]
