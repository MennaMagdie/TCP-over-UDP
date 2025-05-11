import threading
import time
from reliable_udp import ReliableUDP

def server():
    r_server = ReliableUDP(local_ip="127.0.0.1", local_port=5000)
    print("Server waiting for message...")
    message = r_server.receive()
    print(f"[Server] Received: {message}")
    r_server.close()

def client():
    time.sleep(1)  # server starts first
    r_client = ReliableUDP(local_ip="127.0.0.1", local_port=6000,
                           remote_ip="127.0.0.1", remote_port=5000)
    r_client.send("Hello from client!", flags="DAT")
    print("[Client] Message sent.")
    r_client.close()


server_thread = threading.Thread(target=server)
client_thread = threading.Thread(target=client)

server_thread.start()
client_thread.start()

server_thread.join()
client_thread.join()
