from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get API key from environment
API_KEY = os.getenv('VIDEO_DOWNLOAD_API_KEY', '')

@app.route('/proxy/download', methods=['GET'])
def proxy_download():
    """Proxy for video download API to avoid CORS"""
    try:
        if not API_KEY:
            return jsonify({'error': 'API key not configured on server'}), 500
            
        # Get all query parameters from frontend
        params = {
            'format': request.args.get('format'),
            'url': request.args.get('url'),
            'apikey': API_KEY,  # Use backend API key
            'add_info': request.args.get('add_info', '1'),
        }
        
        # Optional parameters
        if request.args.get('audio_quality'):
            params['audio_quality'] = request.args.get('audio_quality')
        if request.args.get('allow_extended_duration'):
            params['allow_extended_duration'] = request.args.get('allow_extended_duration')
        if request.args.get('no_merge'):
            params['no_merge'] = request.args.get('no_merge')
        if request.args.get('audio_language'):
            params['audio_language'] = request.args.get('audio_language')
        if request.args.get('start_time'):
            params['start_time'] = request.args.get('start_time')
        if request.args.get('end_time'):
            params['end_time'] = request.args.get('end_time')
        
        # Build URL with parameters
        api_url = 'https://p.savenow.to/ajax/download.php'
        response = requests.get(api_url, params=params)
        
        # Get response data and filter out message field
        response_data = response.json()
        if 'message' in response_data:
            del response_data['message']
        
        return jsonify(response_data), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy/progress', methods=['GET'])
def proxy_progress():
    """Proxy for progress check to avoid CORS"""
    try:
        job_id = request.args.get('id')
        
        # Make request to actual API
        api_url = f"https://p.savenow.to/ajax/progress?id={job_id}"
        response = requests.get(api_url)
        
        # Get response data and filter out message field
        response_data = response.json()
        if 'message' in response_data:
            del response_data['message']
        
        return jsonify(response_data), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy/file', methods=['GET'])
def proxy_file():
    """Proxy for actual file download to avoid CORS and hide original headers"""
    try:
        download_url = request.args.get('url')
        
        # Stream the file from the download URL with minimal headers
        response = requests.get(download_url, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Get filename from Content-Disposition or use default
        filename = 'download.mp3'
        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        
        # Create response with only necessary headers (hiding original source)
        return app.response_class(
            response.iter_content(chunk_size=8192),
            mimetype=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': response.headers.get('Content-Length', ''),
                'Cache-Control': 'no-cache',
                'X-Content-Type-Options': 'nosniff'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
