# Dockerfile
# This file defines the complete environment for the application.

# 1. Start from a lean and official Python base image.
FROM python:3.11-slim

# 2. Install Google Chrome and its dependencies.
RUN apt-get update && apt-get install -y wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container.
WORKDIR /app

# 4. Copy and install Python requirements.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your application code.
COPY app.py .

# 6. Let Render set the port.
ENV PORT 10000

# 7. THIS IS THE CRITICAL START COMMAND.
# This CMD line is now the definitive command that Render will execute.
# It correctly uses the eventlet worker required for WebSockets.
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "--worker-class", "eventlet", "-w", "1", "app:app"]
