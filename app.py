import os
from flask import Flask, render_template_string, request, send_file
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

# Initialize Flask App
app = Flask(__name__)

# --- HTML Template ---
# For simplicity, the HTML is included directly in the Python file.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Page Visitor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 40px;
            background-color: #f8f9fa;
            color: #343a40;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        .container {
            background-color: #ffffff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #007bff;
            text-align: center;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        input[type="url"] {
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 16px;
        }
        input[type="submit"] {
            padding: 10px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.2s;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        .results {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eeeeee;
        }
        .results h2 {
            color: #28a745;
        }
        .results p {
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 4px;
        }
        .results img {
            max-width: 100%;
            border: 1px solid #ced4da;
            border-radius: 4px;
            margin-top: 10px;
        }
        .loader {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Human-Like Web Visitor</h1>
        <form action="/visit" method="post" onsubmit="showLoader()">
            <label for="url">Enter a URL to visit:</label>
            <input type="url" id="url" name="url" required placeholder="https://www.example.com">
            <input type="submit" value="Visit URL">
        </form>
        <div class="loader" id="loader">
            <p>Visiting the URL, please wait...</p>
        </div>
    </div>

    <script>
        function showLoader() {
            document.getElementById('loader').style.display = 'block';
        }
    </script>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visit Results</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 40px;
            background-color: #f8f9fa;
            color: #343a40;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        .container {
            background-color: #ffffff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-width: 800px;
            width: 100%;
        }
        a {
            color: #007bff;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .results h2 {
            color: #28a745;
        }
        .results p {
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 4px;
            word-wrap: break-word;
        }
        .results img {
            max-width: 100%;
            border: 1px solid #ced4da;
            border-radius: 4px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/">&larr; Back to Home</a>
        <div class="results">
            <h2>Visit Successful!</h2>
            <p><b>Page Title:</b> {{ title }}</p>
            <p>Here is a screenshot of the page:</p>
            <img src="/screenshot.png" alt="Screenshot of the visited page">
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Renders the main page with the URL input form."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/visit', methods=['POST'])
def visit():
    """
    Visits the URL provided in the form using Selenium.
    Returns the page title and a screenshot.
    """
    url = request.form.get('url')
    if not url:
        return "URL is required.", 400

    # --- Selenium Configuration ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Essential for Render
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Human-like headers
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # Recent versions of Selenium can manage the driver automatically.
    # We do not need to specify the executable_path.
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the page
        driver.get(url)
        
        # Add a small delay to allow page to load
        time.sleep(2)

        # Get page title
        page_title = driver.title

        # Take a screenshot and save it
        screenshot_path = os.path.join('/tmp', 'screenshot.png')
        driver.save_screenshot(screenshot_path)

    except Exception as e:
        return f"An error occurred: {e}", 500
    finally:
        if 'driver' in locals():
            driver.quit()

    return render_template_string(RESULT_TEMPLATE, title=page_title)


@app.route('/screenshot.png')
def screenshot():
    """Serves the captured screenshot."""
    return send_file(os.path.join('/tmp', 'screenshot.png'), mimetype='image/png')


if __name__ == '__main__':
    app.run(debug=True)
