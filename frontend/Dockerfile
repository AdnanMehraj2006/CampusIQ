FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN npm run build

EXPOSE 5173

CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-5173}"]
