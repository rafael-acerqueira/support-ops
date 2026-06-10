FROM node:18-alpine AS builder

WORKDIR /app

# Copy root package files
COPY package.json pnpm-lock.yaml ./

# Copy app package
COPY apps/web ./apps/web

# Copy packages if any shared libs
COPY packages ./packages

RUN npm install --frozen-lockfile

RUN npm run build --filter=web

FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/package.json ./apps/web/
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start", "--filter=web"]
