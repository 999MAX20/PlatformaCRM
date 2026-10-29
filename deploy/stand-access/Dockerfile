FROM node:24-alpine
WORKDIR /app
COPY --chown=node:node gate.mjs page.mjs brand.json ./
RUN mkdir /state && chown node:node /state
USER node
EXPOSE 8080
CMD ["node", "gate.mjs"]
