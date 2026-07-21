#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.parse
import subprocess
import signal
import time
import sys
import threading
import atexit
import logging
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("rtsp-relay")

CONFIG_PATH = "/usr/blueos/extensions/mediamtx/mediamtx.yml"
MEDIAMTX_BIN = "./mediamtx"
mediamtx_process = None
mediamtx_lock = threading.Lock()

def start_mediamtx():
    """Start the MediaMTX process"""
    global mediamtx_process
    with mediamtx_lock:
        try:
            # Kill any existing process first
            stop_mediamtx()
            
            # Start new process
            logger.info("Starting MediaMTX...")
            mediamtx_process = subprocess.Popen(
                [MEDIAMTX_BIN, CONFIG_PATH],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd="/app"
            )
            
            # Start a thread to read output
            threading.Thread(
                target=read_process_output,
                args=(mediamtx_process,),
                daemon=True
            ).start()
            
            logger.info(f"MediaMTX started with PID {mediamtx_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start MediaMTX: {str(e)}")
            return False

def stop_mediamtx():
    """Stop the MediaMTX process if it's running"""
    global mediamtx_process
    if mediamtx_process is not None:
        try:
            logger.info(f"Stopping MediaMTX (PID {mediamtx_process.pid})...")
            mediamtx_process.terminate()
            # Wait up to 5 seconds for graceful termination
            for _ in range(50):
                if mediamtx_process.poll() is not None:
                    break
                time.sleep(0.1)
            # Force kill if still running
            if mediamtx_process.poll() is None:
                logger.warning("MediaMTX did not terminate gracefully, forcing...")
                mediamtx_process.kill()
            mediamtx_process = None
            logger.info("MediaMTX stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop MediaMTX: {str(e)}")
            return False
    return True  # Already stopped

def restart_mediamtx():
    """Restart the MediaMTX process"""
    logger.info("Restarting MediaMTX...")
    return start_mediamtx()

def read_process_output(process):
    """Read and log output from the process"""
    for line in iter(process.stdout.readline, b''):
        line_str = line.decode().strip()
        if "error" in line_str.lower():
            logger.error(f"[MediaMTX] {line_str}")
        else:
            logger.info(f"[MediaMTX] {line_str}")

def cleanup():
    """Clean up resources on exit"""
    logger.info("Shutting down, cleaning up resources...")
    stop_mediamtx()

# Register cleanup handler
atexit.register(cleanup)

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override log_message to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()
        
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # API endpoint to get YAML content
        if path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            try:
                with open(CONFIG_PATH, 'r') as file:
                    self.wfile.write(file.read().encode())
            except Exception as e:
                error_msg = f"Error reading config: {str(e)}"
                logger.error(error_msg)
                self.wfile.write(error_msg.encode())
            return
        
        # API endpoint to list configured stream paths (for the WebRTC viewer grid)
        if path == '/api/paths':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            names = []
            try:
                with open(CONFIG_PATH, 'r') as file:
                    cfg = yaml.safe_load(file) or {}
                paths = cfg.get('paths') or {}
                for name in paths.keys():
                    # Skip catch-all and regex paths: they can't form a concrete WHEP URL
                    if name in ('all', 'all_others'):
                        continue
                    if isinstance(name, str) and name.startswith('~'):
                        continue
                    names.append(name)
            except Exception as e:
                logger.error(f"Error reading paths from config: {str(e)}")
            self.wfile.write(json.dumps({'paths': names}).encode())
            return

        # API endpoint to restart MediaMTX without changing config
        if path == '/api/restart':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            restart_success = restart_mediamtx()
            self.wfile.write(json.dumps({
                'success': restart_success
            }).encode())
            return
        
        # Serve index.html for the root path
        if path == '/' or path == '':
            self.path = '/index.html'
        
        # Serve webrtc.html for the /webrtc path
        elif path == '/webrtc':
            self.path = '/webrtc.html'
            
        # Pass through for all other requests
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # API endpoint to save YAML content
        if path == '/api/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                
                # Write to config file
                with open(CONFIG_PATH, 'w') as file:
                    file.write(post_data)
                
                logger.info(f"Configuration saved to {CONFIG_PATH}")
                
                # Restart MediaMTX after config update
                restart_success = restart_mediamtx()
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'restart': restart_success
                }).encode())
            except Exception as e:
                error_msg = f"Failed to save configuration: {str(e)}"
                logger.error(error_msg)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
            return
        
        # Default handler for other POST requests
        self.send_response(404)
        self.end_headers()

def run_server(port=8908):
    try:
        # Change to the directory containing index.html
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # First start MediaMTX
        if not start_mediamtx():
            logger.warning("Failed to start MediaMTX, continuing anyway...")
        
        # Then start the web server
        server_address = ('', port)
        httpd = HTTPServer(server_address, CORSRequestHandler)
        logger.info(f'Starting web server on port {port}...')
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in server: {str(e)}")
    finally:
        cleanup()

if __name__ == '__main__':
    run_server() 