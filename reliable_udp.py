import socket
import json
import hashlib
import random
import time

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

        # Error simulation parameters
        self.simulate_packet_loss = False
        self.packet_loss_rate = 0.0
        self.simulate_corruption = False
        self.corruption_rate = 0.0

        #Retransmission parameters
        self.max_retransmissions = 5
        self.retransmission_count = 0

        # Debugging parameters
        self.debug = False

    def calculate_checksum(self, data):
        return hashlib.md5(data.encode()).hexdigest()

    def false_checksum(self, checksum):
        """Simulate a false checksum for testing purposes."""
        chars = list(checksum)
        position=random.randint(0, len(chars)-1)
        chars[position] = random.choice('0123456789abcdef')
        return ''.join(chars)
        
        
    def set_debug_mode(self, debug):
        self.debug = debug
    
    def debug_print(self, message):
        if self.debug:
            print(f"{message}")

    def configure_error_simulation(self, packet_loss_rate=0.0, corruption_rate=0.0):
        """Configure error simulation parameters."""
        if 0<= packet_loss_rate <= 1.0:
            self.simulate_packet_loss = packet_loss_rate > 0
            self.packet_loss_rate = packet_loss_rate
        else:
            raise ValueError("Packet loss rate must be between 0 and 1")
        if 0<= corruption_rate <= 1.0:
            self.simulate_corruption = corruption_rate > 0
            self.corruption_rate = corruption_rate
        else:
            raise ValueError("Corruption rate must be between 0 and 1")
        self.debug_print(f"Packet loss rate set to {self.packet_loss_rate}, Corruption rate set to {self.corruption_rate}")

  
        
    def make_packet(self, data, seq, flags="DAT"):
        checksum = self.calculate_checksum(data)

        # Simulate packet corruption if enabled
        if self.simulate_corruption and random.random() < self.corruption_rate:
            self.debug_print("Simulating packet corruption")
            checksum = self.false_checksum(checksum)

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

    def should_simulate_packet_loss(self):
        """Determine if packet loss should be simulated."""
        # True if packet should be "lost", False otherwise
        if self.simulate_packet_loss and random.random() < self.packet_loss_rate:
            self.debug_print("Simulating packet loss")
            return True
        return False
    
    def send(self, data, flags="DAT"):
        if not self.remote_addr:
            raise ValueError("Remote address not set")
        packet = self.make_packet(data, self.seq, flags)

        self.retransmission_count = 0

        while self.retransmission_count < self.max_retransmissions:

            if self.should_simulate_packet_loss():
                self.debug_print(f"Simulating packet loss (seq={self.seq})")
                time.sleep(self.timeout)  # Simulate timeout
            else:
                self.socket.sendto(packet, self.remote_addr)
                self.debug_print(f"Packet sent (seq={self.seq}, flags={flags})")
            
            try:
                response, _ = self.socket.recvfrom(4096)
                ack_packet = self.parse_packet(response)
                if ack_packet and ack_packet["flags"] == "ACK" and ack_packet["ack"] == self.seq:
                    self.debug_print(f"ACK received (ack={ack_packet['ack']})")
                    self.seq = 1 - self.seq  # Toggle sequence number (0/1 for Stop-and-Wait)
                    return True
                else:
                    self.debug_print("Invalid or corrupted ACK, retransmitting...")
                    
            except socket.timeout:
                self.retransmission_count += 1
                self.debug_print(f"Timeout #{self.retransmission_count}, retransmitting...")
                
                if self.retransmission_count > self.max_retransmissions:
                    self.debug_print("Maximum retransmissions reached, connection failed")
                    return False
        return False

    def receive(self):
        while True:
            try:
                packet_bytes, addr = self.socket.recvfrom(4096)
                packet = self.parse_packet(packet_bytes)
                if packet:
                    self.debug_print(f"Packet received (seq={packet['seq']}, flags={packet['flags']})")
                    if packet["seq"] == self.seq:
                        self.remote_addr = addr
                        self.send_ack(packet["seq"])  # Send ACK for the received sequence
                        self.seq = 1 - self.seq
                        return packet["data"]
                    else:
                        self.debug_print("Duplicate packet, re-ACKing")
                        self.send_ack(packet["seq"])  # Resend ACK if duplicated
            except socket.timeout:
                continue

    def send_ack(self,ack_seq):
        ack_packet = {
            "seq": 0,
            "ack": ack_seq,
            "flags": "ACK",
            "data": "",
            "checksum": self.calculate_checksum("")
        }
        # Simulate packet loss for ACKs too
        if not self.should_simulate_packet_loss():
            self.socket.sendto(json.dumps(ack_packet).encode(), self.remote_addr)
            self.debug_print(f"ACK sent (ack={ack_seq})")
        else:
            self.debug_print(f"Simulating ACK loss (ack={ack_seq})")


    def establish_connection(self, remote_ip=None, remote_port=None):
        if remote_ip and remote_port:
            self.remote_addr = (remote_ip, remote_port)
            self.debug_print(f"Connection established with {self.remote_addr}")
        if not self.remote_addr:
            raise ValueError("Remote address not set")
        
        self.debug_print(f"Establishing connection to {self.remote_addr}")
        
        # Send SYN
        if not self.send("", flags="SYN"):
            return False
            
        # Wait for SYN-ACK
        try:
            data = self.receive()
            if data == "":  # Empty data with SYN-ACK flag
                # Send final ACK (handled in receive())
                self.debug_print("Connection established")
                return True
        except Exception as e:
            self.debug_print(f"Connection failed: {e}")
            
        return False
    
    def accept_connection(self):
        self.debug_print("Waiting for connection request")
        while True:
            try:
                packet_bytes, addr = self.socket.recvfrom(4096)
                packet = self.parse_packet(packet_bytes)
                
                if packet and packet["flags"] == "SYN":
                    self.debug_print(f"SYN received from {addr}")
                    self.remote_addr = addr
                    
                    # Send SYN-ACK
                    if self.send("", flags="SYNACK"):
                        # Third part of handshake is handled by normal receive/ACK
                        self.debug_print("Connection established")
                        return True
                    else:
                        self.debug_print("Failed to send SYNACK")
                        
            except socket.timeout:
                continue       
        return False

    def close_connection(self):
        if self.remote_addr:
            self.debug_print("Initiating connection termination")
            
            # Send FIN
            self.send("", flags="FIN")
            
            try:
                # Wait for FIN-ACK
                packet_bytes, addr = self.socket.recvfrom(4096)
                packet = self.parse_packet(packet_bytes)
                
                if packet and packet["flags"] == "FINACK":
                    self.debug_print("Received FIN-ACK, connection closed gracefully")
            except socket.timeout:
                self.debug_print("No FIN-ACK received, closing anyway")
                
                
        self.close()


    def close(self):
        self.socket.close()
        self.debug_print("Socket closed")
