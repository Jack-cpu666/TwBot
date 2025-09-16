# Dockerfile
# This file defines the complete environment for the interactive browser application.

# 1. Start from a lean and official Python base image.
FROM python:3.11-slim

# 2. Install Google Chrome and its dependencies.
# Using the official Google repository is more reliable than the default Debian package.
RUN apt-get update && apt-get install -y wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container.
WORKDIR /app

# 4. Copy the Python requirements file first. This optimizes Docker's layer caching.
# If requirements.txt doesn't change, Docker won't reinstall the packages on every build.
COPY requirements.txt .

# 5. Install the Python packages.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code into the container.
# This assumes your main file is named app.py.
COPY app.py .

# 7. Set the environment variable for the port.
# Render will dynamically assign a port, and Gunicorn will read this variable.
ENV PORT 10000

# 8. This default command is now corrected. While the render.yaml `startCommand`
# takes precedence, it is best practice for the Dockerfile to contain the correct
# command so it can run correctly anywhere.
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "--worker-class", "eventlet", "-w", "1", "app:app"]
