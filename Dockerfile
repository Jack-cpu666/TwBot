# Use a lean version of Python as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# [THIS IS THE KEY PART]
# Install system dependencies needed for Chrome, then install Chrome itself.
# This all runs as 'root' inside the container, so no 'sudo' is needed.
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # Clean up to keep the image size down
    && rm -rf /var/lib/apt/lists/*

# Copy your Python requirements file and install them
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Tell the container what command to run when it starts.
# We use gunicorn for a production-ready server.
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:$PORT", "app:app"]
