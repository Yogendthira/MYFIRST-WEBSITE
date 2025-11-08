import socket
import json
import threading
import pyautogui
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KeyboardController
import time

# ============= SERVER (Friend's Laptop) =============

class CursorServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.mouse_controller = MouseController()
        self.keyboard_controller = KeyboardController()
        self.remote_cursor_pos = (0, 0)
        
    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        
        try:
            while True:
                client, addr = self.server.accept()
                print(f"[SERVER] Client connected from {addr}")
                self.clients.append(client)
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("[SERVER] Shutting down...")
            self.server.close()
    
    def handle_client(self, client, addr):
        try:
            while True:
                data = client.recv(1024)
                if not data:
                    break
                
                command = json.loads(data.decode('utf-8'))
                self.process_command(command)
                
        except Exception as e:
            print(f"[SERVER] Error from {addr}: {e}")
        finally:
            self.clients.remove(client)
            client.close()
            print(f"[SERVER] Client {addr} disconnected")
    
    def process_command(self, command):
        try:
            if command['type'] == 'move':
                x, y = command['x'], command['y']
                self.remote_cursor_pos = (x, y)
                # Optional: You could draw something here if using GUI
                
            elif command['type'] == 'click':
                x, y = command['x'], command['y']
                self.mouse_controller.position = (x, y)
                self.mouse_controller.click()
                print(f"[SERVER] Clicked at ({x}, {y})")
                
            elif command['type'] == 'scroll':
                dy = command['dy']
                self.mouse_controller.scroll(0, dy)
                print(f"[SERVER] Scrolled by {dy}")
                
            elif command['type'] == 'key':
                key = command['key']
                self.keyboard_controller.press(key)
                self.keyboard_controller.release(key)
                print(f"[SERVER] Pressed key: {key}")
                
        except Exception as e:
            print(f"[SERVER] Error processing command: {e}")
    
    def broadcast_cursor_pos(self):
        data = json.dumps({
            'type': 'cursor_pos',
            'x': self.remote_cursor_pos[0],
            'y': self.remote_cursor_pos[1]
        }).encode('utf-8')
        
        for client in self.clients[:]:
            try:
                client.send(data)
            except:
                if client in self.clients:
                    self.clients.remove(client)


# ============= CLIENT (Your System) =============

class CursorClient:
    def __init__(self, server_host='localhost', server_port=5000):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mouse_listener = None
        self.keyboard_listener = None
        
    def connect(self):
        try:
            self.socket.connect((self.server_host, self.server_port))
            print(f"[CLIENT] Connected to {self.server_host}:{self.server_port}")
            self.start_listeners()
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False
        return True
    
    def start_listeners(self):
        # Start mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_scroll
        )
        self.mouse_listener.start()
        
        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press
        )
        self.keyboard_listener.start()
        
        print("[CLIENT] Listeners started")
    
    def on_mouse_move(self, x, y):
        try:
            command = json.dumps({
                'type': 'move',
                'x': x,
                'y': y
            }).encode('utf-8')
            self.socket.send(command)
        except Exception as e:
            print(f"[CLIENT] Error sending move: {e}")
    
    def on_mouse_click(self, x, y, button, pressed):
        if pressed:
            try:
                command = json.dumps({
                    'type': 'click',
                    'x': x,
                    'y': y
                }).encode('utf-8')
                self.socket.send(command)
                print(f"[CLIENT] Sent click at ({x}, {y})")
            except Exception as e:
                print(f"[CLIENT] Error sending click: {e}")
    
    def on_scroll(self, x, y, dx, dy):
        try:
            command = json.dumps({
                'type': 'scroll',
                'dy': -1 if dy < 0 else 1
            }).encode('utf-8')
            self.socket.send(command)
            print(f"[CLIENT] Sent scroll")
        except Exception as e:
            print(f"[CLIENT] Error sending scroll: {e}")
    
    def on_key_press(self, key):
        try:
            # Convert key to string
            if hasattr(key, 'char') and key.char:
                key_str = key.char
            elif hasattr(key, 'name'):
                key_str = key.name
            else:
                return
            
            command = json.dumps({
                'type': 'key',
                'key': key_str
            }).encode('utf-8')
            self.socket.send(command)
            print(f"[CLIENT] Sent key: {key_str}")
        except Exception as e:
            print(f"[CLIENT] Error sending key: {e}")
    
    def close(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.socket.close()
        print("[CLIENT] Disconnected")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python script.py server")
        print("  python script.py client <host> [port]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == 'server':
        server = CursorServer()
        server.start()
    
    elif mode == 'client':
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
        
        client = CursorClient(host, port)
        if client.connect():
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[CLIENT] Shutting down...")
                client.close()
    
    else:
        print("Invalid mode. Use 'server' or 'client'")