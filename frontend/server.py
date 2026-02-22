from flask import Flask, send_from_directory, request
import os

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    # Always serve index.html for root, regardless of query params
    return send_from_directory('.', 'index.html')

@app.route('/index.html')
def index_html():
    # Explicitly handle index.html requests with query params
    return send_from_directory('.', 'index.html')

@app.route('/bulk')
@app.route('/bulk.html')
def bulk():
    return send_from_directory('.', 'bulk.html')

@app.route('/ytdownload')
@app.route('/ytdownload.html')
def ytdownload():
    return send_from_directory('.', 'ytdownload.html')

@app.route('/<path:path>')
def serve_static(path):
    # Check if the path is a file that exists
    file_path = os.path.join('.', path)
    if os.path.isfile(file_path):
        return send_from_directory('.', path)
    # If not a file, serve index.html (for client-side routing)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    print("Frontend running at http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=True)
