FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Installa Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installa PostgreSQL client (per psql)
RUN apt-get update \
    && apt-get install -y postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /workspace
