# Stage 1: Build frontend
FROM docker.io/oven/bun:latest AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN bun install
COPY frontend/ ./
RUN bun run build

# Stage 2: Final image (Backend & Nginx)
FROM docker.io/library/python:3.10-slim
WORKDIR /app

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install nginx
RUN apt-get update && apt-get install -y nginx openssl && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ /app/backend/

# Install backend dependencies using uv
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1
RUN uv sync --no-dev

# Copy built frontend
WORKDIR /app
COPY --from=frontend-build /app/dist /var/www/html

# Create a non-root user and set permissions
RUN useradd -m -s /bin/bash appuser && \
    mkdir -p /var/cache/nginx /var/run /var/log/nginx /var/lib/nginx /app/backend/instance /etc/nginx/ssl /etc/nginx/dynamic && \
    touch /etc/nginx/dynamic/banned_ips.conf && \
    chown -R appuser:appuser /var/cache/nginx /var/run /var/log/nginx /var/lib/nginx /app /var/www/html /etc/nginx/ssl /etc/nginx/dynamic

# Remove default user directive from nginx.conf so it can run as non-root
# and relocate the PID file to /tmp
RUN sed -i 's/user www-data;//g' /etc/nginx/nginx.conf && \
    sed -i 's|/run/nginx.pid|/tmp/nginx.pid|g' /etc/nginx/nginx.conf

# Configure Nginx
COPY nginx.conf /etc/nginx/sites-available/default

# Expose ports
EXPOSE 8080 8443

# Start Nginx and Flask
COPY start.sh /start.sh
RUN chmod +x /start.sh && chown appuser:appuser /start.sh

# Switch to non-root user
USER appuser

# Add virtual environment to PATH if needed, though start.sh explicitly calls uv run
ENV PATH="/app/backend/.venv/bin:$PATH"

CMD ["/start.sh"]
