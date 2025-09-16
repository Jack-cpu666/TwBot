# Use a lean version of Python as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies and Google Chrome using the modern, secure key management method.
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    --no-install-recommends \
    # Download the Google Chrome signing key, de-armor it, and save it to the trusted keyrings directory
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    # Add the Google Chrome repository, pointing it to the key we just saved
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    # Update package lists again to include the new repository, then install Chrome
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # Clean up to keep the image size down
    && rm -rf /var/lib/apt/lists/*

# Copy your Python requirements file and install them
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Use the shell form of CMD for environment variable substitution.
# Add --timeout and --log-level for a more stable, production-ready server.
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 --log-level debug app:app
