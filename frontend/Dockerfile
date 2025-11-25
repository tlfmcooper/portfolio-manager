# Build stage
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Install dependencies first to leverage Docker cache
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json ./package-lock.json

# Install dependencies
RUN npm install -g npm@latest && \
    npm install -g vite && \
    npm install

# Copy source code
COPY frontend/. .

# Accept build argument for API URL
# Railway automatically passes environment variables as build args
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Debug: Show the API URL during build
RUN echo "Building with VITE_API_URL=${VITE_API_URL}"

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration from builder stage
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
