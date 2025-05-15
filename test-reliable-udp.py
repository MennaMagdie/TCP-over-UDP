import threading
import time
from reliable_udp import ReliableUDP

def test_normal_connection():
    print("\n--- Test: Normal Connection/Disconnection ---")
    
    def server():
        r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15001)
        r_server.set_debug_mode(True)
        print("[Server] Waiting for connection...")
        if r_server.accept_connection():
            print("[Server] Connection accepted.")
            message = r_server.receive()
            print(f"[Server] Received: {message}")
            r_server.close_connection()
        else:
            print("[Server] Connection failed.")
        r_server.close()

    def client():
        time.sleep(0.5)
        r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16001,
                               remote_ip="127.0.0.1", remote_port=15001)
        r_client.set_debug_mode(True)
        print("[Client] Establishing connection...")
        if r_client.establish_connection():
            print("[Client] Connection established.")
            if r_client.send("Test normal connection.", flags="DAT"):
                print("[Client] Message sent successfully.")
            else:
                print("[Client] Failed to send message.")
            r_client.close_connection()
        else:
            print("[Client] Connection failed.")
        r_client.close()

    s = threading.Thread(target=server)
    c = threading.Thread(target=client)
    s.start()
    c.start()
    s.join()
    c.join()
    print("Normal connection test done.\n")


def test_various_message_sizes():
    print("\n--- Test: Data Transfer with Different Message Sizes ---")

    messages = [
        "Short",
        "Medium message size test." * 10,
        "Large message: " + ("x" * 1000),
    ]

    def server():
        r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15002)
        r_server.set_debug_mode(True)
        print("[Server] Waiting for connection...")
        if r_server.accept_connection():
            print("[Server] Connection accepted.")
            for _ in messages:
                msg = r_server.receive()
                print(f"[Server] Received message size: {len(msg)}")
            r_server.close_connection()
        else:
            print("[Server] Connection failed.")
        r_server.close()

    def client():
        time.sleep(0.5)
        r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16002,
                               remote_ip="127.0.0.1", remote_port=15002)
        r_client.set_debug_mode(True)
        print("[Client] Establishing connection...")
        if r_client.establish_connection():
            print("[Client] Connection established.")
            for msg in messages:
                success = r_client.send(msg, flags="DAT")
                print(f"[Client] Sent message of size {len(msg)}: {'Success' if success else 'Fail'}")
            r_client.close_connection()
        else:
            print("[Client] Connection failed.")
        r_client.close()

    s = threading.Thread(target=server)
    c = threading.Thread(target=client)
    s.start()
    c.start()
    s.join()
    c.join()
    print("Data transfer test done.\n")


def test_error_simulation(packet_loss_rate, corruption_rate):
    print(f"\n--- Test: Error Simulation (Loss: {packet_loss_rate}, Corruption: {corruption_rate}) ---")

    def server():
        r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15003)
        r_server.set_debug_mode(True)
        r_server.configure_error_simulation(packet_loss_rate=packet_loss_rate, corruption_rate=corruption_rate)
        print("[Server] Waiting for connection...")
        if r_server.accept_connection():
            print("[Server] Connection accepted.")
            msg = r_server.receive()
            print(f"[Server] Received: {msg}")
            r_server.close_connection()
        else:
            print("[Server] Connection failed.")
        r_server.close()

    def client():
        time.sleep(0.5)
        r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16003,
                               remote_ip="127.0.0.1", remote_port=15003)
        r_client.set_debug_mode(True)
        r_client.configure_error_simulation(packet_loss_rate=packet_loss_rate, corruption_rate=corruption_rate)
        print("[Client] Establishing connection...")
        if r_client.establish_connection():
            print("[Client] Connection established.")
            success = r_client.send("Testing error simulation", flags="DAT")
            print(f"[Client] Message send status: {'Success' if success else 'Failed'}")
            r_client.close_connection()
        else:
            print("[Client] Connection failed.")
        r_client.close()

    s = threading.Thread(target=server)
    c = threading.Thread(target=client)
    s.start()
    c.start()
    s.join()
    c.join()
    print("Error simulation test done.\n")


def test_simultaneous_close():
    print("\n--- Test: Simultaneous Close ---")

    def server():
        r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15004)
        r_server.set_debug_mode(True)
        print("[Server] Waiting for connection...")
        if r_server.accept_connection():
            print("[Server] Connection accepted.")
            time.sleep(1)  # Wait before closing to simulate simultaneous close
            r_server.close_connection()
        else:
            print("[Server] Connection failed.")
        r_server.close()

    def client():
        time.sleep(0.2)
        r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16004,
                               remote_ip="127.0.0.1", remote_port=15004)
        r_client.set_debug_mode(True)
        print("[Client] Establishing connection...")
        if r_client.establish_connection():
            print("[Client] Connection established.")
            time.sleep(1)  # Wait before closing to simulate simultaneous close
            r_client.close_connection()
        else:
            print("[Client] Connection failed.")
        r_client.close()

    s = threading.Thread(target=server)
    c = threading.Thread(target=client)
    s.start()
    c.start()
    s.join()
    c.join()
    print("Simultaneous close test done.\n")


def test_timeouts_and_retransmissions():
    print("\n--- Test: Timeouts and Retransmission ---")

    # For this test, set a high packet loss to force retransmission attempts
    high_loss = 0.4

    def server():
        r_server = ReliableUDP(local_ip="127.0.0.1", local_port=15005)
        r_server.set_debug_mode(True)
        r_server.configure_error_simulation(packet_loss_rate=high_loss, corruption_rate=0)
        print("[Server] Waiting for connection...")
        if r_server.accept_connection():
            print("[Server] Connection accepted.")
            msg = r_server.receive()
            print(f"[Server] Received: {msg}")
            r_server.close_connection()
        else:
            print("[Server] Connection failed.")
        r_server.close()

    def client():
        time.sleep(0.5)
        r_client = ReliableUDP(local_ip="127.0.0.1", local_port=16005,
                               remote_ip="127.0.0.1", remote_port=15005)
        r_client.set_debug_mode(True)
        r_client.configure_error_simulation(packet_loss_rate=high_loss, corruption_rate=0)
        print("[Client] Establishing connection...")
        if r_client.establish_connection():
            print("[Client] Connection established.")
            success = r_client.send("Testing retransmission under high packet loss", flags="DAT")
            print(f"[Client] Message send status: {'Success' if success else 'Failed'}")
            r_client.close_connection()
        else:
            print("[Client] Connection failed.")
        r_client.close()

    s = threading.Thread(target=server)
    c = threading.Thread(target=client)
    s.start()
    c.start()
    s.join()
    c.join()
    print("Timeouts and retransmission test done.\n")


if __name__ == "__main__":
    test_normal_connection()
    test_various_message_sizes()
    test_error_simulation(packet_loss_rate=0.1, corruption_rate=0.05)
    test_simultaneous_close()
    test_timeouts_and_retransmissions()
    
    print("All tests completed.")
