# app.py
# FINAL, SHARED BROWSER VERSION - All users interact with the same instance.

# --- CRUCIAL ---
# Move monkey_patch() to the absolute top of the file, before any other imports.
import eventlet
eventlet.monkey_patch()

import os
import base64
import time
from io import BytesIO
import shutil
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# --- Find the Chrome Executable Path Automatically ---
# This is important for both local and Render environments.
CHROME_EXECUTABLE_PATH = shutil.which('google-chrome-stable')
if not CHROME_EXECUTABLE_PATH:
    # This error will be helpful for debugging if Chrome isn't installed correctly on the server.
    raise RuntimeError(
        "FATAL ERROR: Could not find 'google-chrome-stable' in the system's PATH. "
        "Ensure Google Chrome is installed and accessible."
    )
print(f"--- Found Chrome executable at: {CHROME_EXECUTABLE_PATH} ---")

# --- Initialize the Flask App and SocketIO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'shared-secret-key!'
socketio = SocketIO(app, async_mode='eventlet')

# --- Global State for the SINGLE, SHARED Browser Instance ---
# We use global variables to hold the one driver instance and manage its state.
shared_browser_driver = None
connected_clients = 0
shared_framerate = 5  # Default framerate

# --- The Complete User Interface (HTML, CSS, JavaScript) ---
# This self-contained template provides the entire frontend.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Shared Interactive Browser</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background-color: #2c2f33; color: #fff; }
        #container { display: flex; flex-direction: column; height: 100%; }
        #controls { padding: 8px; background-color: #23272a; display: flex; gap: 10px; align-items: center; border-bottom: 1px solid #4f545c; }
        #nav-form { flex-grow: 1; display: flex; }
        #url-input { flex-grow: 1; padding: 8px 12px; border-radius: 4px 0 0 4px; border: 1px solid #4f545c; background-color: #40444b; color: #fff; font-size: 14px; }
        #go-button { padding: 8px 15px; border-radius: 0 4px 4px 0; border: none; background-color: #7289da; color: white; cursor: pointer; font-weight: bold; }
        #go-button:hover { background-color: #677bc4; }
        #status { font-size: 0.9em; min-width: 150px; text-align: center; }
        #quality-control { display: flex; align-items: center; gap: 5px;}
        #browser-view { flex-grow: 1; position: relative; background-color: #36393f; display: flex; justify-content: center; align-items: center; }
        #screen { max-width: 100%; max-height: 100%; cursor: crosshair; background-color: #000; }
        #overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; text-align: center; flex-direction: column; z-index: 10; }
        #overlay h1 { margin: 0; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>
    <div id="container">
        <div id="controls">
            <form id="nav-form">
                <input type="url" id="url-input" placeholder="Enter a URL to start or change the page" required>
                <button id="go-button" type="submit">Go</button>
            </form>
            <div id="quality-control">
                <label for="framerate">FPS:</label>
                <input type="range" id="framerate" min="1" max="10" value="5" step="1">
            </div>
            <div id="status">Status: Disconnected</div>
        </div>
        <div id="browser-view">
            <div id="overlay">
                <div>
                    <h1>Welcome to the Shared Remote Browser</h1>
                    <p>Enter a URL above to begin the session for everyone.</p>
                </div>
            </div>
            <img id="screen" alt="Remote Browser Screen">
        </div>
    </div>
    <script>
        const socket = io();
        const screen = document.getElementById('screen');
        const statusEl = document.getElementById('status');
        const overlay = document.getElementById('overlay');
        const urlInput = document.getElementById('url-input');
        const navForm = document.getElementById('nav-form');
        const framerateSlider = document.getElementById('framerate');
        let isBrowserStarted = false;

        socket.on('connect', () => { statusEl.textContent = 'Status: Connected'; });
        socket.on('disconnect', () => { statusEl.textContent = 'Status: Disconnected'; });
        socket.on('connect_error', (err) => { statusEl.textContent = `Error: ${err.message}`; });
        
        socket.on('screenshot', (data) => {
            screen.src = `data:image/jpeg;base64,${data.image}`;
            if (overlay.style.display !== 'none') {
                overlay.style.display = 'none';
            }
            isBrowserStarted = true;
        });

        socket.on('page_info', (data) => {
            urlInput.value = data.url;
            document.title = data.title;
        });

        socket.on('browser_stopped', () => {
            overlay.innerHTML = "<h1>Welcome to the Shared Remote Browser</h1><p>The session has ended. Enter a new URL to begin.</p>";
            overlay.style.display = 'flex';
            isBrowserStarted = false;
        });

        navForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = urlInput.value;
            if (url) {
                overlay.innerHTML = "<h1>Starting shared browser...</h1>";
                overlay.style.display = 'flex';
                socket.emit('start_browser', { url: url });
            }
        });

        screen.addEventListener('click', (e) => {
            if (!isBrowserStarted) return;
            const rect = screen.getBoundingClientRect();
            const scaleX = screen.naturalWidth / rect.width;
            const scaleY = screen.naturalHeight / rect.height;
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            socket.emit('input_event', { type: 'click', x: x, y: y });
        });

        screen.addEventListener('wheel', (e) => {
            if (!isBrowserStarted) return;
            e.preventDefault();
            socket.emit('input_event', { type: 'scroll', deltaY: e.deltaY });
        });

        document.addEventListener('keydown', (e) => {
            if (!isBrowserStarted || e.target.id === 'url-input') return;
            e.preventDefault();
            socket.emit('input_event', {
                type: 'keydown',
                key: e.key,
                code: e.code,
                ctrlKey: e.ctrlKey,
                metaKey: e.metaKey,
                shiftKey: e.shiftKey
            });
        });

        framerateSlider.addEventListener('input', (e) => {
            socket.emit('settings_change', { framerate: parseInt(e.target.value) });
        });
    </script>
</body>
</html>
"""

def stream_screenshots():
    """ The screenshot streaming loop is now global and broadcasts to everyone. """
    global shared_browser_driver, shared_framerate
    print("--- Starting screenshot streaming loop. ---")
    while shared_browser_driver:
        try:
            img_bytes = BytesIO(shared_browser_driver.get_screenshot_as_png())
            b64_image = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
            
            # Broadcast to ALL connected clients.
            socketio.emit('screenshot', {'image': b64_image})
            socketio.emit('page_info', {'url': shared_browser_driver.current_url, 'title': shared_browser_driver.title})
        except Exception as e:
            print(f"[STREAM-ERROR] Error in streaming thread: {e}")
            break # Exit loop if browser crashes or is closed
        
        sleep_duration = 1.0 / shared_framerate
        socketio.sleep(sleep_duration)
    print("--- Screenshot streaming stopped. ---")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Add a dedicated health check route for Render
@app.route('/health')
def health_check():
    return "OK", 200

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    print(f"Client connected. Total clients: {connected_clients}")

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients, shared_browser_driver
    connected_clients -= 1
    print(f"Client disconnected. Total clients: {connected_clients}")
    
    # Shut down the browser only if the LAST client disconnects.
    if connected_clients <= 0 and shared_browser_driver:
        print("--- Last client disconnected. Shutting down shared browser. ---")
        try:
            shared_browser_driver.quit()
        except Exception as e:
            print(f"Error while quitting driver: {e}")
        finally:
            shared_browser_driver = None
            # Tell any lingering clients that the browser is gone
            socketio.emit('browser_stopped')

@socketio.on('start_browser')
def handle_start_browser(data):
    global shared_browser_driver
    
    url = data.get('url', 'https://www.google.com/ncr')

    # If a browser is already running, just navigate to the new URL.
    if shared_browser_driver:
        print(f"Browser already running. Navigating to: {url}")
        try:
            shared_browser_driver.get(url)
        except Exception as e:
            print(f"Error navigating to new URL: {e}")
        return

    try:
        print(f"--- Starting SHARED browser session for all users at URL: {url} ---")
        
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,720")
        
        driver = uc.Chrome(
            options=options,
            browser_executable_path=CHROME_EXECUTABLE_PATH
        )
        
        driver.get(url)
        shared_browser_driver = driver
        
        # Start the one and only screenshot loop as a background task.
        socketio.start_background_task(target=stream_screenshots)
    except Exception as e:
        print(f"[START-ERROR] Error starting browser: {e}")
        socketio.emit('error', {'message': str(e)})

@socketio.on('input_event')
def handle_input_event(data):
    # Direct all input events to the single shared browser driver.
    if not shared_browser_driver: return
    
    event_type = data.get('type')
    try:
        if event_type == 'click':
            x, y = data['x'], data['y']
            ActionChains(shared_browser_driver).move_by_offset(x, y).click().move_by_offset(-x, -y).perform()
        elif event_type == 'scroll':
            delta_y = data.get('deltaY', 0)
            shared_browser_driver.execute_script(f"window.scrollBy(0, {delta_y});")
        elif event_type == 'keydown':
            key = data.get('key')
            active_element = shared_browser_driver.switch_to.active_element
            active_element.send_keys(key)
    except Exception as e:
        print(f"[INPUT-ERROR] Error processing '{event_type}': {e}")
        
@socketio.on('settings_change')
def handle_settings_change(data):
    global shared_framerate
    if 'framerate' in data:
        new_rate = int(data['framerate'])
        if 1 <= new_rate <= 10:
            shared_framerate = new_rate

# This is the entry point for local execution
if __name__ == '__main__':
    print("--- Starting local development server in SHARED MODE ---")
    print("--- Access the application at http://localhost:5001 ---")
    socketio.run(app, debug=True, port=5001)
