import socket
import json
import os
import threading
from datetime import datetime

# Configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
FILES_DIR = 'files'
DEFAULT_USER = 'student'
DEFAULT_PASSWORD = '1234'
FILE_HISTORY = {}


def safe_filename(filename):
    """Normalize filenames to prevent path traversal"""
    return os.path.basename(filename or '').strip()


def record_history(filename, operation, details=''):
    """Store file operation history in memory"""
    safe_name = safe_filename(filename)
    if not safe_name:
        return

    entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {operation}"
    if details:
        entry = f"{entry} | {details}"

    FILE_HISTORY.setdefault(safe_name, []).append(entry)


def rename_history(old_name, new_name):
    """Move history to the renamed file"""
    old_key = safe_filename(old_name)
    new_key = safe_filename(new_name)
    if not old_key or not new_key:
        return

    history = FILE_HISTORY.pop(old_key, [])
    FILE_HISTORY[new_key] = history
    record_history(new_key, 'rename', f'{old_key} -> {new_key}')

def ensure_files_dir():
    """Ensure files directory exists"""
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"✓ Directory '{FILES_DIR}' created")


def authenticate(username, password):
    """Authenticate user"""
    return username == DEFAULT_USER and password == DEFAULT_PASSWORD


def handle_client(conn, addr):
    """Handle client connection"""
    print(f"\n🔗 Client connected from {addr}")
    authenticated = False
    current_user = None
    
    try:
        while True:
            # Receive request
            request_data = conn.recv(4096).decode('utf-8')
            if not request_data:
                break
            
            try:
                request = json.loads(request_data)
                command = request.get('command')
                
                print(f"📨 Command received: {command}")
                
                # Authentication
                if command == 'login':
                    username = request.get('username')
                    password = request.get('password')
                    
                    if authenticate(username, password):
                        authenticated = True
                        current_user = username
                        response = {'status': 'success', 'message': f'Welcome {username}!'}
                        print(f"✓ User {username} authenticated")
                    else:
                        response = {'status': 'error', 'message': 'Invalid credentials'}
                        print(f"✗ Authentication failed for user {username}")
                
                elif not authenticated:
                    response = {'status': 'error', 'message': 'Not authenticated. Use login first'}
                
                # File operations
                elif command == 'create_file':
                    filename = safe_filename(request.get('filename'))
                    content = request.get('content', '')
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                        conn.send(json.dumps(response).encode('utf-8'))
                        continue
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    record_history(filename, 'create', f'{len(content)} characters')
                    
                    response = {'status': 'success', 'message': f'File {filename} created on server'}
                    print(f"✓ File created: {filename}")
                
                elif command == 'upload':
                    filename = safe_filename(request.get('filename'))
                    content = request.get('content')
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                        conn.send(json.dumps(response).encode('utf-8'))
                        continue
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    record_history(filename, 'upload', f'{len(content or "")} characters')
                    
                    response = {'status': 'success', 'message': f'File {filename} uploaded'}
                    print(f"✓ File uploaded: {filename}")
                
                elif command == 'rename_file':
                    old_name = safe_filename(request.get('old_name'))
                    new_name = safe_filename(request.get('new_name'))
                    if not old_name or not new_name:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        old_path = os.path.join(FILES_DIR, old_name)
                        new_path = os.path.join(FILES_DIR, new_name)
                        if not os.path.exists(old_path):
                            response = {'status': 'error', 'message': f'File {old_name} not found'}
                        elif os.path.exists(new_path):
                            response = {'status': 'error', 'message': f'File {new_name} already exists'}
                        else:
                            os.rename(old_path, new_path)
                            rename_history(old_name, new_name)
                            response = {'status': 'success', 'message': f'File {old_name} renamed to {new_name}'}
                            print(f"✓ File renamed: {old_name} -> {new_name}")
                
                elif command == 'read_file':
                    filename = safe_filename(request.get('filename'))
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File {filename} not found'}
                        else:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            record_history(filename, 'read', f'{len(content)} characters')
                            response = {'status': 'success', 'message': f'Content of {filename}', 'content': content}
                            print(f"✓ File read: {filename}")
                
                elif command == 'download':
                    filename = safe_filename(request.get('filename'))
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File {filename} not found'}
                        else:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            record_history(filename, 'download', f'{len(content)} characters')
                            response = {'status': 'success', 'message': f'File {filename} downloaded', 'filename': filename, 'content': content}
                            print(f"✓ File downloaded: {filename}")
                
                elif command == 'edit_file':
                    filename = safe_filename(request.get('filename'))
                    content = request.get('content', '')
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File {filename} not found'}
                        else:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content)
                            record_history(filename, 'edit', f'{len(content)} characters')
                            response = {'status': 'success', 'message': f'File {filename} updated'}
                            print(f"✓ File edited: {filename}")
                
                elif command == 'see_file_operation_history':
                    filename = safe_filename(request.get('filename'))
                    if not filename:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        history = FILE_HISTORY.get(filename, [])
                        response = {'status': 'success', 'message': f'History for {filename}', 'history': history}
                        print(f"✓ History sent for: {filename}")
                
                elif command == 'list_files':
                    files = sorted([name for name in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, name))])
                    response = {'status': 'success', 'files': files}
                    print(f"✓ Files listed: {len(files)} files found")
                
                elif command == 'logout':
                    authenticated = False
                    current_user = None
                    response = {'status': 'success', 'message': 'Logged out'}
                    print(f"✓ User logged out")
                
                else:
                    response = {'status': 'error', 'message': f'Unknown command: {command}'}
                
            except Exception as e:
                response = {'status': 'error', 'message': str(e)}
                print(f"✗ Error: {str(e)}")
            
            # Send response
            conn.send(json.dumps(response).encode('utf-8'))
    
    except Exception as e:
        print(f"✗ Connection error: {str(e)}")
    finally:
        conn.close()
        print(f"🔌 Client disconnected from {addr}")


def start_server():
    """Start FTP server"""
    ensure_files_dir()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    
    print("=" * 60)
    print("🚀 FTP SERVER STARTED")
    print("=" * 60)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print(f"Files Directory: {FILES_DIR}")
    print(f"Default User: {DEFAULT_USER}")
    print(f"Default Password: {DEFAULT_PASSWORD}")
    print("=" * 60)
    
    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n\n⛔ Server shutting down...")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()
