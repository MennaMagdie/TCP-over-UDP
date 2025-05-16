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
        self.connected = False
        self.closing = False  # flag for connection termination

        # Error simulation parameters
        self.simulate_packet_loss = False
        self.packet_loss_rate = 0.0
        self.simulate_corruption = False
        self.corruption_rate = 0.0

        # Retransmission parameters
        self.max_retransmissions = 5
        self.retransmission_count = 0

        # Debugging parameters
        self.debug = False

    def calculate_checksum(self, data):
        return hashlib.md5(data.encode()).hexdigest()

    def false_checksum(self, checksum):
        """Simulate a false checksum for testing purposes."""
        chars = list(checksum)
        position = random.randint(0, len(chars)-1)
        chars[position] = random.choice('0123456789abcdef')
        return ''.join(chars)
        
    def set_debug_mode(self, debug):
        self.debug = debug
    
    def debug_print(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def configure_error_simulation(self, packet_loss_rate=0.0, corruption_rate=0.0):
        if 0 <= packet_loss_rate <= 1.0:
            self.simulate_packet_loss = packet_loss_rate > 0
            self.packet_loss_rate = packet_loss_rate
        else:
            raise ValueError("Packet loss rate must be between 0 and 1")
            
        if 0 <= corruption_rate <= 1.0:
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
            required_fields = ["seq", "ack", "flags", "data", "checksum"]
            if not all(field in packet for field in required_fields):
                self.debug_print("Malformed packet: missing required fields")
                return None
                
            calc_checksum = self.calculate_checksum(packet["data"])
            if calc_checksum != packet["checksum"]:
                self.debug_print(f"Checksum mismatch: expected {calc_checksum}, got {packet['checksum']}")
                return None
            return packet
        except Exception as e:
            self.debug_print(f"Error parsing packet: {e}")
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
                self.debug_print(f"Simulating packet loss (seq={self.seq}, flags={flags})")
                time.sleep(self.timeout)  # Simulate timeout
            else:
                self.socket.sendto(packet, self.remote_addr)
                self.debug_print(f"Packet sent (seq={self.seq}, flags={flags})")
            
            try:
                response, addr = self.socket.recvfrom(4096)
                ack_packet = self.parse_packet(response)
                
                if not ack_packet:
                    self.debug_print("Corrupted packet received, retransmitting...")
                    self.retransmission_count += 1
                    continue
                
                # Handle simultaneous close: if we're sending FIN and receive a FIN from peer
                if flags == "FIN" and ack_packet["flags"] == "FIN":
                    self.debug_print(f"Simultaneous close detected, sending FINACK")
                    self.send_finack(ack_packet["seq"])
                    # We're already trying to close, so just consider this success
                    self.seq = 1 - self.seq
                    self.connected = False
                    return True
                    
                # For handshake, handle SYNACK response differently
                if flags == "SYN" and ack_packet["flags"] == "SYNACK":
                    self.debug_print(f"SYNACK received (seq={ack_packet['seq']}, ack={ack_packet['ack']})")
                    self.ack = ack_packet['seq']
                    # Send ACK for SYNACK
                    self.send_ack(ack_packet["seq"])
                    self.seq = 1 - self.seq  # Toggle sequence number
                    self.connected = True
                    return True
                    
                # Regular ACK handling
                elif ack_packet["flags"] == "ACK" and ack_packet["ack"] == self.seq:
                    self.debug_print(f"ACK received (ack={ack_packet['ack']})")
                    self.seq = 1 - self.seq  # Toggle sequence number (0/1 for Stop-and-Wait)
                    return True
                    
                # Handle FIN-ACK
                elif flags == "FIN" and ack_packet["flags"] == "FINACK":
                    self.debug_print(f"FINACK received")
                    self.send_ack(ack_packet["seq"]) # ACK from the client (to confirm clean close)
                    self.connected = False
                    return True
                    
                else:
                    self.debug_print(f"Invalid ACK received (expected ack={self.seq}, got ack={ack_packet['ack']}, flags={ack_packet['flags']})")
                    
            except socket.timeout:
                self.retransmission_count += 1
                self.debug_print(f"Timeout #{self.retransmission_count}, retransmitting...")
                
                if self.retransmission_count >= self.max_retransmissions:
                    self.debug_print("Maximum retransmissions reached, connection failed")
                    return False
        return False

    def receive(self, expected_flags=None):
        max_attempts = 10  
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            try:
                packet_bytes, addr = self.socket.recvfrom(4096)
                packet = self.parse_packet(packet_bytes)
                
                if not packet:
                    self.debug_print("Corrupted packet received, waiting for retransmission...")
                    continue
                    
                self.debug_print(f"Packet received (seq={packet['seq']}, flags={packet['flags']})")
                
                # Handle specific flag expectations
                if expected_flags and packet["flags"] != expected_flags:
                    self.debug_print(f"Unexpected flags: got {packet['flags']}, expected {expected_flags}")
                    # For SYN when expecting something else, start connection handling
                    if packet["flags"] == "SYN":
                        self.remote_addr = addr
                        self.handle_syn(packet)
                        continue
                    else:
                        # Send ACK but don't return for unexpected flags
                        self.send_ack(packet["seq"])
                        continue
                
                # Special handling for SYN
                if packet["flags"] == "SYN":
                    self.remote_addr = addr
                    return self.handle_syn(packet)
                
                # Special handling for FIN
                if packet["flags"] == "FIN":
                    self.remote_addr = addr
                    # Check if we're also in the process of closing
                    if self.closing:
                        self.debug_print("Detected simultaneous close in receive")
                        self.send_finack(packet["seq"])
                        self.connected = False
                        return ""
                    else:
                        return self.handle_fin(packet)
                
                # Normal data packet handling
                if packet["seq"] == self.seq:
                    self.remote_addr = addr
                    self.send_ack(packet["seq"])  # Send ACK for the received sequence
                    self.seq = 1 - self.seq  # Toggle sequence for next expected packet
                    return packet["data"]
                else:
                    self.debug_print("Duplicate packet, re-ACKing")
                    self.send_ack(packet["seq"])  # Resend ACK if duplicated
                    
            except socket.timeout:
                self.debug_print("Timeout while waiting for packet")
                continue
                
        self.debug_print("Max receive attempts reached")
        return None
        
    def handle_syn(self, packet):
        self.debug_print(f"SYN received, sending SYNACK")
        # Send SYNACK with our sequence number
        synack_packet = {
            "seq": self.seq,
            "ack": packet["seq"],
            "flags": "SYNACK",
            "data": "",
            "checksum": self.calculate_checksum("")
        }
        
        if not self.should_simulate_packet_loss():
            self.socket.sendto(json.dumps(synack_packet).encode(), self.remote_addr)
            self.debug_print(f"SYNACK sent (seq={self.seq}, ack={packet['seq']})")
            
            # Wait for final ACK
            try:
                ack_bytes, _ = self.socket.recvfrom(4096)
                ack_packet = self.parse_packet(ack_bytes)
                
                if ack_packet and ack_packet["flags"] == "ACK" and ack_packet["ack"] == self.seq:
                    self.debug_print("Final handshake ACK received")
                    self.seq = 1 - self.seq  # Toggle sequence for next packet
                    self.connected = True
                    return ""  # Empty data for handshake
            except socket.timeout:
                self.debug_print("Timeout waiting for final handshake ACK")
                
        return None
        
    def handle_fin(self, packet):
        self.debug_print(f"FIN received, sending FINACK")
        # Send FINACK
        self.send_finack(packet["seq"])
        self.connected = False
        return ""  # Empty data for connection termination
    
    def send_finack(self, fin_seq):
        """Send a FINACK packet in response to a FIN."""
        finack_packet = {
            "seq": self.seq,
            "ack": fin_seq,
            "flags": "FINACK",
            "data": "",
            "checksum": self.calculate_checksum("")
        }
        
        if not self.should_simulate_packet_loss():
            self.socket.sendto(json.dumps(finack_packet).encode(), self.remote_addr)
            self.debug_print(f"FINACK sent (seq={self.seq}, ack={fin_seq})")

    def send_ack(self, ack_seq):
        ack_packet = {
            "seq": self.seq,
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
        
        if not self.remote_addr:
            raise ValueError("Remote address not set")

        self.debug_print(f"Establishing connection to {self.remote_addr}")

        # Send SYN
        success = self.send("", flags="SYN")  # empty data with SYN flag

        if success:
            self.debug_print("Connection established successfully")
        else:
            self.debug_print("Connection failed")
        return success

    
    def accept_connection(self):
        self.debug_print("Waiting for connection request")
        
        # Wait for SYN packet
        data = self.receive(expected_flags="SYN")
        if data is not None:  # Connection handshake completed in receive method
            self.debug_print("Connection accepted")
            self.connected = True
            return True
            
        self.debug_print("Connection acceptance failed")
        return False

    def close_connection(self):
        if not self.remote_addr:
            raise ValueError("Remote address not set")

        self.debug_print("Closing connection")
        
        # Set closing flag to handle simultaneous close
        self.closing = True

        # Send FIN
        success = self.send("", flags="FIN")
        
        self.closing = False  # Reset flag

        if success:
            self.debug_print("Connection closed gracefully")
        else:
            self.debug_print("Connection close failed")
        return success

    def close(self):
        """Close the socket."""
        self.socket.close()
        self.debug_print("Socket closed")