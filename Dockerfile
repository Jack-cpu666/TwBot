# Dockerfile
# FINAL VERSION - Uses the correct 'shell form' for the CMD instruction.

# 1. Start from a lean and official Python base image.
FROM python:3.11-slim

# 2. Install Google Chrome using the new, recommended procedure.
RUN apt-get update && apt-get install -y wget gnupg ca-certificates && \
    # Create the directory for keyring files
    mkdir -p /etc/apt/keyrings && \
    # Download the Google Chrome signing key, de-armor it, and save it to the keyring directory
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg && \
    # Create the repository source file, telling it to use the key we just saved
    sh -c 'echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list' && \
    # Update apt lists again now that we have the new repository
    apt-get update && \
    # Install Google Chrome
    apt-get install -y google-chrome-stable fonts-liberation unzip && \
    # Clean up apt lists to keep the image size small
    rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f 3) && \
    wget --no-verbose -O /tmp/chromedriver_linux64.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip && \
    mkdir -p /opt/chromedriver && \
    unzip /tmp/chromedriver_linux64.zip -d /opt/chromedriver && \
    mv /opt/chromedriver/chromedriver-linux64/chromedriver /opt/chromedriver/ && \
    chmod +x /opt/chromedriver/chromedriver && \
    ln -s /opt/chromedriver/chromedriver /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver_linux64.zip

# 3. Set the working directory inside the container.
WORKDIR /app

# 4. Copy and install Python requirements.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your application code.
COPY app.py .

# 6. Let Render set the port.
ENV PORT 10000

# 7. THIS IS THE CRITICAL FIX.
# We now use the 'shell form' (no brackets/quotes) so that the ${PORT}
# environment variable is correctly expanded by the shell.
CMD gunicorn --bind 0.0.0.0:${PORT} --worker-class eventlet -w 1 app:app
