import os
import base64
import time
from io import BytesIO

from flask import Flask, render_template_string
from flask_socketio import SocketIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

# Use eventlet for long-running background tasks
import eventlet
eventlet.monkey_patch()

# --- Initialize App ---
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# --- In-memory session storage ---
# This dictionary will hold the browser driver for each connected user
sessions = {}

# --- HTML & JavaScript Template ---
# This is the user interface for the interactive session
INTERACTIVE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Interactive Remote Browser</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: sans-serif; background-color: #333; color: white; }
        #container { display: flex; flex-direction: column; height: 100%; }
        #controls { padding: 10px; background-color: #444; display: flex; gap: 10px; align-items: center; border-bottom: 1px solid #555;}
        #controls input[type="url"] { flex-grow: 1; padding: 8px; border-radius: 4px; border: 1px solid #666; background-color: #222; color: white;}
        #controls button { padding: 8px 12px; border-radius: 4px; border: none; background-color: #007bff; color: white; cursor: pointer; }
        #browser-view { flex-grow: 1; display: flex; justify-content: center; align-items: center; background-color: #2a2a2a; overflow: hidden; position: relative;}
        #screen { max-width: 100%; max-height: 100%; cursor: crosshair; }
        #status { font-size: 0.9em; }
        #loading-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: none; justify-content: center; align-items: center; font-size: 1.5em; z-index: 10;}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>
    <div id="container">
        <div id="controls">
            <form id="url-form" style="display: flex; width: 100%; gap: 10px;">
                <input type="url" id="url" placeholder="https://www.example.com" required>
                <button type="submit">Go</button>
            </form>
            <div id="status">Status: Disconnected</div>
        </div>
        <div id="browser-view">
            <div id="loading-overlay">Starting remote browser...</div>
            <img id="screen" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Remote Browser Screen">
        </div>
    </div>

    <script>
        const socket = io();
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        const loadingOverlay = document.getElementById('loading-overlay');
        const urlForm = document.getElementById('url-form');
        const urlInput = document.getElementById('url');

        // Connection events
        socket.on('connect', () => {
            status.textContent = 'Status: Connected';
        });

        socket.on('disconnect', () => {
            status.textContent = 'Status: Disconnected';
        });

        // Handle screenshot stream from server
        socket.on('screenshot', (data) => {
            screen.src = `data:image/jpeg;base64,${data.image}`;
            loadingOverlay.style.display = 'none';
        });

        // Start browser when form is submitted
        urlForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = urlInput.value;
            if (url) {
                loadingOverlay.style.display = 'flex';
                socket.emit('start_browser', { url: url });
            }
        });

        // Handle user input events
        screen.addEventListener('click', (e) => {
            const rect = screen.getBoundingClientRect();
            // Calculate coordinates relative to the image's actual displayed size
            const scaleX = screen.naturalWidth / rect.width;
            const scaleY = screen.naturalHeight / rect.height;
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            socket.emit('input_event', { type: 'click', x: x, y: y });
        });
    </script>
</body>
</html>
"""

# --- Background Thread for Streaming ---
def stream_screenshots(sid):
    """Continuously sends screenshots to a specific client."""
    driver = sessions.get(sid)
    if not driver:
        return

    while sid in sessions:
        try:
            # Capture screenshot as an in-memory binary stream
            screenshot_io = BytesIO(driver.get_screenshot_as_png())
            
            # Encode as base64
            screenshot_io.seek(0)
            b64_image = base64.b64encode(screenshot_io.read()).decode('utf-8')
            
            # Emit to the client
            socketio.emit('screenshot', {'image': b64_image}, room=sid)
        except Exception as e:
            print(f"Error streaming for {sid}: {e}")
            break # Exit loop on error (e.g., browser closed)
        
        # Control the frame rate
        socketio.sleep(0.5)

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template_string(INTERACTIVE_TEMPLATE)

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up the Selenium driver when a user disconnects."""
    if request.sid in sessions:
        print(f"Client disconnected: {request.sid}. Closing browser.")
        sessions[request.sid].quit()
        del sessions[request.sid]

@socketio.on('start_browser')
def handle_start_browser(data):
    """Launch a new Selenium browser for a user."""
    sid = request.sid
    if sid in sessions:
        sessions[sid].quit() # Close existing browser if any

    url = data.get('url', 'https://www.google.com')
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # The new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,720") # Set a fixed size

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        sessions[sid] = driver
        
        # Start the background task to stream screenshots for this user
        socketio.start_background_task(stream_screenshots, sid)
    except Exception as e:
        print(f"Error starting browser for {sid}: {e}")
        socketio.emit('error', {'message': str(e)}, room=sid)


@socketio.on('input_event')
def handle_input_event(data):
    """Handle user input (clicks, keys, etc.) and translate to Selenium actions."""
    sid = request.sid
    driver = sessions.get(sid)
    if not driver:
        return

    try:
        if data['type'] == 'click':
            x, y = data['x'], data['y']
            # ActionChains needs an element to move relative to, so we use the body
            body = driver.find_element(By.TAG_NAME, 'body')
            ActionChains(driver).move_to_element_with_offset(body, 0, 0).move_by_offset(x, y).click().perform()
            
    except Exception as e:
        print(f"Error processing input for {sid}: {e}")


if __name__ == '__main__':
    # Use Gunicorn for production, this is for local dev only
    socketio.run(app, debug=True, port=5000)
