import threading
import time
from reliable_udp import ReliableUDP

def server():
    r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15000)
    r_server.set_debug_mode(True)
    r_server.configure_error_simulation(packet_loss_rate=0.1, corruption_rate=0.1)
    if r_server.accept_connection():
        print("[Server] Connection accepted.")

        message = r_server.receive()
        print(f"[Server] Received: {message}")

        r_server.close_connection()  # Gracefully terminate connection
    else:
        print("[Server] Connection failed.")
        r_server.close()

def client():
    time.sleep(1)  # server starts first
    r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16000,
                           remote_ip="127.0.0.1", remote_port=15000)
    r_client.set_debug_mode(True)
    r_client.configure_error_simulation(packet_loss_rate=0.1, corruption_rate=0.1)

    if r_client.establish_connection():
        print("[Client] Connection established.")

        success = r_client.send("Hello from client!", flags="DAT")
        if success:
            print("[Client] Message sent.")
        else:
            print("[Client] Failed to send message after retries.")

        r_client.close_connection()
    else:
        print("[Client] Connection failed.")
        r_client.close()

server_thread = threading.Thread(target=server)
client_thread = threading.Thread(target=client)

server_thread.start()
client_thread.start()

server_thread.join()
client_thread.join()
