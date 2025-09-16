import os
from flask import Flask, render_template_string, request, send_file
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Initialize the Flask App
app = Flask(__name__)

# --- HTML & CSS Templates ---
# The user interface is embedded directly into the file for simplicity.

# Template for the home page with the URL input form
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
        .loader {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .error {
            color: #dc3545;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Human-Like Web Visitor</h1>
        <p>Enter a URL and the app will visit it using a headless browser, then return the page title and a screenshot.</p>
        <form action="/visit" method="post" onsubmit="showLoader()">
            <label for="url">Enter a URL to visit:</label>
            <input type="url" id="url" name="url" required placeholder="https://www.example.com">
            <input type="submit" value="Visit URL">
        </form>
        <div class="loader" id="loader">
            <p>Visiting the URL, please wait... This can take up to 30 seconds.</p>
        </div>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
    <script>
        function showLoader() {
            document.getElementById('loader').style.display = 'block';
        }
    </script>
</body>
</html>
"""

# Template for displaying the results
RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visit Results</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 40px; background-color: #f8f9fa; color: #343a40; display: flex; justify-content: center; align-items: center; flex-direction: column; }
        .container { background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 800px; width: 100%; }
        a { color: #007bff; text-decoration: none; display: inline-block; margin-bottom: 20px;}
        a:hover { text-decoration: underline; }
        .results h2 { color: #28a745; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .results p { background-color: #e9ecef; padding: 10px; border-radius: 4px; word-wrap: break-word; font-size: 16px; }
        .results img { max-width: 100%; border: 1px solid #ced4da; border-radius: 4px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/">&larr; Visit Another URL</a>
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
    """Visits the URL provided in the form using Selenium."""
    url = request.form.get('url')
    if not url:
        return render_template_string(HTML_TEMPLATE, error="URL is required."), 400

    # --- Selenium Configuration for Render ---
    # These options are crucial for running Chrome in a headless Linux environment.
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Mimic a real user agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')
    
    driver = None
    try:
        # Selenium will find the ChromeDriver installed by the buildpack automatically.
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the page
        driver.get(url)
        
        # Add a small delay to allow JavaScript to load
        time.sleep(2)

        # Get page title
        page_title = driver.title

        # Render uses a temporary filesystem at /tmp for file storage
        screenshot_path = os.path.join('/tmp', 'screenshot.png')
        driver.save_screenshot(screenshot_path)

    except Exception as e:
        # Clean up the driver if an error occurs
        if driver:
            driver.quit()
        # Return an error to the user
        error_message = f"An error occurred: {e}"
        return render_template_string(HTML_TEMPLATE, error=error_message), 500
    
    # Quit the driver to free up resources
    driver.quit()
    
    # Show the results page
    return render_template_string(RESULT_TEMPLATE, title=page_title)

@app.route('/screenshot.png')
def screenshot():
    """Serves the captured screenshot file."""
    # This route is called by the <img> tag in the result template
    return send_file(os.path.join('/tmp', 'screenshot.png'), mimetype='image/png')

if __name__ == '__main__':
    # This block is for local development. Render will use Gunicorn.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
