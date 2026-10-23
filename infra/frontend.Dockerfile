# Local Vite server only; not a production static asset host.
FROM node:24.22.1-bookworm-slim
WORKDIR /app
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund && chown -R node:node /app
COPY --chown=node:node frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY --chown=node:node frontend/src ./src
USER node
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
