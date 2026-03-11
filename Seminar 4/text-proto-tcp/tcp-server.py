import socket
import threading

HOST = "127.0.0.1"
PORT = 3333
BUFFER_SIZE = 1024
is_running = threading.Event()
is_running.set()

class State:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def add(self, key, value):
        with self.lock:
            if key in self.data:
                return "ERROR key already exists"
            self.data[key] = value
        return "OK - record added"

    def get(self, key):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            return f"DATA {self.data[key]}"

    def remove(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)
                return "OK value deleted"
            return "ERROR invalid key"

    def list_items(self):
        with self.lock:
            if not self.data:
                return "DATA|"
            joined = ",".join(f"{key}={value}" for key, value in self.data.items())
            return f"DATA|{joined}"

    def count(self):
        with self.lock:
            return f"DATA {len(self.data)}"

    def clear(self):
        with self.lock:
            self.data.clear()
        return "all data deleted"

    def update(self, key, new_value):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            self.data[key] = new_value
        return "Data updated"

    def pop(self, key):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            value = self.data.pop(key)
        return f"Data {value}"

state = State()

def process_command(command):
    parts = command.split()
    if not parts:
        return "ERROR empty command", False, False

    cmd = parts[0].upper()

    if cmd == "ADD":
        if len(parts) < 3:
            return "ERROR invalid format", False, False
        return state.add(parts[1], " ".join(parts[2:])), False, False

    if cmd == "GET":
        if len(parts) != 2:
            return "ERROR invalid format", False, False
        return state.get(parts[1]), False, False

    if cmd == "REMOVE":
        if len(parts) != 2:
            return "ERROR invalid format", False, False
        return state.remove(parts[1]), False, False

    if cmd == "LIST":
        if len(parts) != 1:
            return "ERROR invalid format", False, False
        return state.list_items(), False, False

    if cmd == "COUNT":
        if len(parts) != 1:
            return "ERROR invalid format", False, False
        return state.count(), False, False

    if cmd == "CLEAR":
        if len(parts) != 1:
            return "ERROR invalid format", False, False
        return state.clear(), False, False

    if cmd == "UPDATE":
        if len(parts) < 3:
            return "ERROR invalid format", False, False
        return state.update(parts[1], " ".join(parts[2:])), False, False

    if cmd == "POP":
        if len(parts) != 2:
            return "ERROR invalid format", False, False
        return state.pop(parts[1]), False, False

    if cmd == "QUIT":
        is_running.clear()
        return "BYE", True, True

    return "ERROR unknown command", False, False

def handle_client(client_socket):
    with client_socket:
        while is_running.is_set():
            try:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break

                command = data.decode('utf-8').strip()
                response, close_client, _ = process_command(command)
                
                response_data = f"{len(response)} {response}".encode('utf-8')
                client_socket.sendall(response_data)

                if close_client:
                    break

            except Exception as e:
                client_socket.sendall(f"Error: {str(e)}".encode('utf-8'))
                break

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        server_socket.settimeout(1)
        print(f"[SERVER] Listening on {HOST}:{PORT}")

        threads = []
        while is_running.is_set():
            try:
                client_socket, addr = server_socket.accept()
                print(f"[SERVER] Connection from {addr}")
                thread = threading.Thread(target=handle_client, args=(client_socket,))
                thread.start()
                threads.append(thread)
            except socket.timeout:
                continue

        for thread in threads:
            thread.join()

if __name__ == "__main__":
    start_server()
