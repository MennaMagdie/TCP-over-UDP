import socket
import json
import hashlib
# import time

class ReliableUDP:
    def __init__(self, local_ip, local_port, remote_ip=None, remote_port=None, timeout=2):
        self.local_addr = (local_ip, local_port)
        self.remote_addr = (remote_ip, remote_port) if remote_ip and remote_port else None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.local_addr)
        self.socket.settimeout(timeout)
        self.seq = 0
        self.ack = 0
        self.timeout = timeout

    def calculate_checksum(self, data):
        return hashlib.md5(data.encode()).hexdigest()

    def make_packet(self, data, seq, flags="DAT"):
        checksum = self.calculate_checksum(data)
        packet = {
            "seq": seq,
            "ack": self.ack,
            "flags": flags,
            "data": data,
            "checksum": checksum
        }
        return json.dumps(packet).encode()

    def parse_packet(self, packet_bytes):
        try:
            packet = json.loads(packet_bytes.decode())
            calc_checksum = self.calculate_checksum(packet["data"])
            if calc_checksum != packet["checksum"]:
                return None
            return packet
        except:
            return None

    def send(self, data, flags="DAT"):
        if not self.remote_addr:
            raise ValueError("Remote address not set")
        packet = self.make_packet(data, self.seq, flags)
        while True:
            self.socket.sendto(packet, self.remote_addr)
            print(f"Packet sent (seq={self.seq})")
            try:
                response, _ = self.socket.recvfrom(4096)
                ack_packet = self.parse_packet(response)
                if ack_packet and ack_packet["flags"] == "ACK" and ack_packet["ack"] == self.seq:
                    print("ACK received")
                    self.seq = 1 - self.seq
                    return
            except socket.timeout:
                print("Timeout, resending...")

    def receive(self):
        while True:
            try:
                packet_bytes, addr = self.socket.recvfrom(4096)
                packet = self.parse_packet(packet_bytes)
                if packet:
                    if packet["seq"] == self.seq:
                        print(f"Packet received (seq={packet['seq']}, flags={packet['flags']})")
                        self.remote_addr = addr
                        self.send_ack()
                        self.seq = 1 - self.seq
                        return packet["data"]
                    else:
                        print("Duplicate packet, re-ACKing")
                        self.send_ack()  # Resend ACK if duplicated
            except socket.timeout:
                continue

    def send_ack(self):
        ack_packet = {
            "seq": 0,
            "ack": self.seq,
            "flags": "ACK",
            "data": "",
            "checksum": self.calculate_checksum("")
        }
        self.socket.sendto(json.dumps(ack_packet).encode(), self.remote_addr)

    def close(self):
        self.socket.close()
