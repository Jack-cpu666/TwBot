import os
import base64
import time
from io import BytesIO
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Use eventlet as the async provider for our long-running background tasks
import eventlet
eventlet.monkey_patch()

# --- Initialize the Flask App and SocketIO ---
app = Flask(__name__)
# A secret key is needed for session management
app.config['SECRET_KEY'] = 'your-very-secret-key!' 
socketio = SocketIO(app, async_mode='eventlet')

# --- In-memory session storage ---
# This dictionary will hold the browser driver and settings for each connected user.
# The key is the user's unique session ID (sid).
sessions = {}

# --- The Complete User Interface (HTML, CSS, JavaScript) ---
# This is the front-end that the user will interact with.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Advanced Interactive Browser</title>
    <style>
        /* Basic layout and theme */
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background-color: #2c2f33; color: #fff; }
        #container { display: flex; flex-direction: column; height: 100%; }

        /* Control bar styling */
        #controls { padding: 8px; background-color: #23272a; display: flex; gap: 10px; align-items: center; border-bottom: 1px solid #4f545c; }
        #nav-form { flex-grow: 1; display: flex; }
        #url-input { flex-grow: 1; padding: 8px 12px; border-radius: 4px 0 0 4px; border: 1px solid #4f545c; background-color: #40444b; color: #fff; font-size: 14px; }
        #go-button { padding: 8px 15px; border-radius: 0 4px 4px 0; border: none; background-color: #7289da; color: white; cursor: pointer; font-weight: bold; }
        #go-button:hover { background-color: #677bc4; }
        #status { font-size: 0.9em; min-width: 150px; text-align: center; }
        #quality-control { display: flex; align-items: center; gap: 5px;}

        /* Main browser view area */
        #browser-view { flex-grow: 1; position: relative; background-color: #36393f; display: flex; justify-content: center; align-items: center; }
        #screen { max-width: 100%; max-height: 100%; cursor: crosshair; background-color: #000; }

        /* Loading and info overlays */
        #overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; text-align: center; flex-direction: column; z-index: 10; }
        #overlay h1 { margin: 0; }
    </style>
    <!-- The Socket.IO client library -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>
    <div id="container">
        <!-- Top control bar -->
        <div id="controls">
            <form id="nav-form">
                <input type="url" id="url-input" placeholder="Enter a URL and press Enter" required>
                <button id="go-button" type="submit">Go</button>
            </form>
            <div id="quality-control">
                <label for="framerate">FPS:</label>
                <input type="range" id="framerate" min="1" max="10" value="5" step="1">
            </div>
            <div id="status">Status: Disconnected</div>
        </div>

        <!-- Main view where the remote browser is displayed -->
        <div id="browser-view">
            <div id="overlay">
                <div>
                    <h1>Welcome to the Remote Interactive Browser</h1>
                    <p>Enter a URL above to begin.</p>
                </div>
            </div>
            <img id="screen" alt="Remote Browser Screen">
        </div>
    </div>

    <script>
        // --- Initialize connection and DOM elements ---
        const socket = io();
        const screen = document.getElementById('screen');
        const statusEl = document.getElementById('status');
        const overlay = document.getElementById('overlay');
        const urlInput = document.getElementById('url-input');
        const navForm = document.getElementById('nav-form');
        const framerateSlider = document.getElementById('framerate');

        let isBrowserStarted = false;

        // --- Socket Event Handlers ---
        socket.on('connect', () => { statusEl.textContent = 'Status: Connected'; });
        socket.on('disconnect', () => { statusEl.textContent = 'Status: Disconnected'; });
        socket.on('connect_error', (err) => { statusEl.textContent = `Error: ${err.message}`; });

        // This is the core loop: update the screen with the new image from the server
        socket.on('screenshot', (data) => {
            screen.src = `data:image/jpeg;base64,${data.image}`;
            if (!isBrowserStarted) {
                overlay.style.display = 'none';
                isBrowserStarted = true;
            }
        });
        
        // Update the URL bar with the current URL of the remote browser
        socket.on('page_info', (data) => {
            urlInput.value = data.url;
            document.title = data.title; // Update the tab title
        });

        // Handle errors from the server
        socket.on('error', (data) => {
            overlay.innerHTML = `<h1>Error: ${data.message}</h1><p>Try again or check server logs.</p>`;
            overlay.style.display = 'flex';
        });


        // --- User Input Event Emitters ---
        
        // Start the browser session
        navForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = urlInput.value;
            if (url) {
                overlay.innerHTML = "<h1>Starting remote browser...</h1>";
                overlay.style.display = 'flex';
                socket.emit('start_browser', { url: url, width: screen.clientWidth, height: screen.clientHeight });
            }
        });

        // Handle clicks
        screen.addEventListener('click', (e) => {
            if (!isBrowserStarted) return;
            const rect = screen.getBoundingClientRect();
            const scaleX = screen.naturalWidth / rect.width;
            const scaleY = screen.naturalHeight / rect.height;
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            socket.emit('input_event', { type: 'click', x: x, y: y });
        });

        // Handle mouse wheel for scrolling
        screen.addEventListener('wheel', (e) => {
            if (!isBrowserStarted) return;
            e.preventDefault();
            socket.emit('input_event', { type: 'scroll', deltaY: e.deltaY });
        });
        
        // Handle keyboard input
        document.addEventListener('keydown', (e) => {
            if (!isBrowserStarted || e.target.id === 'url-input') return; // Don't capture typing in the URL bar
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

        // Handle quality/framerate slider
        framerateSlider.addEventListener('input', (e) => {
            socket.emit('settings_change', { framerate: parseInt(e.target.value) });
        });

    </script>
</body>
</html>
"""

# --- Background Task to Stream Screenshots ---
def stream_screenshots(sid):
    """
    This function runs in a background greenlet for each user, continuously
    capturing and sending screenshots of their dedicated browser.
    """
    session = sessions.get(sid)
    if not session or not session.get('driver'):
        return

    driver = session['driver']
    
    while sid in sessions:
        try:
            # Capture screenshot as an in-memory binary stream
            img_bytes = BytesIO(driver.get_screenshot_as_png())
            img_bytes.seek(0)
            b64_image = base64.b64encode(img_bytes.read()).decode('utf-8')
            
            # Emit the image and current page info to the specific client
            socketio.emit('screenshot', {'image': b64_image}, room=sid)
            socketio.emit('page_info', {'url': driver.current_url, 'title': driver.title}, room=sid)

        except Exception as e:
            print(f"[{sid}] Error in streaming thread: {e}")
            break  # Exit the loop if the browser crashes or is closed

        # Control the frame rate based on user setting, with a default
        framerate = sessions.get(sid, {}).get('framerate', 5)
        sleep_duration = 1.0 / framerate
        socketio.sleep(sleep_duration)

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main interactive browser page."""
    return render_template_string(HTML_TEMPLATE)

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """A new user has connected."""
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """A user has disconnected. We must clean up their browser instance."""
    if request.sid in sessions:
        print(f"Client disconnected: {request.sid}. Cleaning up browser session.")
        sessions[request.sid]['driver'].quit()
        del sessions[request.sid]

@socketio.on('start_browser')
def handle_start_browser(data):
    """Event to launch a new Selenium browser for a user."""
    sid = request.sid
    if sid in sessions:
        sessions[sid]['driver'].quit()

    url = data.get('url', 'https://google.com/ncr') # ncr = no country redirect
    width = data.get('width', 1280)
    height = data.get('height', 720)

    try:
        print(f"[{sid}] Starting browser with size {width}x{height} at URL: {url}")
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/google-chrome"
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--window-size={width},{height}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # Store the driver and settings in our session dictionary
        sessions[sid] = {'driver': driver, 'framerate': 5}
        
        # Start the dedicated background task to stream screenshots for this new session
        socketio.start_background_task(target=stream_screenshots, sid=sid)
    except Exception as e:
        print(f"[{sid}] Error starting browser: {e}")
        socketio.emit('error', {'message': f"Failed to start browser: {str(e)}"}, room=sid)

@socketio.on('input_event')
def handle_input_event(data):
    """Handles all user interactions (clicks, keys, scrolls) and translates them to Selenium actions."""
    sid = request.sid
    session = sessions.get(sid)
    if not session:
        return

    driver = session['driver']
    event_type = data.get('type')

    try:
        if event_type == 'click':
            x, y = data['x'], data['y']
            # We perform a click relative to the top-left of the page body
            ActionChains(driver).move_by_offset(x, y).click().move_by_offset(-x, -y).perform()

        elif event_type == 'scroll':
            delta_y = data.get('deltaY', 0)
            # Use JavaScript execution for smooth scrolling
            driver.execute_script(f"window.scrollBy(0, {delta_y});")

        elif event_type == 'keydown':
            key = data.get('key')
            # Handle special keys and general typing
            if key in Keys.__dict__:
                action_key = Keys.__dict__[key]
            else:
                action_key = key
            
            # Find the currently active element to send keys to
            active_element = driver.switch_to.active_element
            active_element.send_keys(action_key)

    except Exception as e:
        print(f"[{sid}] Error processing input event '{event_type}': {e}")
        
@socketio.on('settings_change')
def handle_settings_change(data):
    """Updates session settings, like framerate."""
    sid = request.sid
    if sid in sessions and 'framerate' in data:
        sessions[sid]['framerate'] = int(data['framerate'])

# --- Main entry point for the application ---
if __name__ == '__main__':
    # This is for local development. Render will use the Gunicorn command.
    print("Starting Flask-SocketIO server for local development...")
    socketio.run(app, debug=True, port=5001)
