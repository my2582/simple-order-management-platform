#!/usr/bin/env python
"""Check IB API port availability."""

import socket

def test_port(host, port, description):
    """Test if port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ {description} (Port {port}): OPEN")
            return True
        else:
            print(f"❌ {description} (Port {port}): CLOSED")
            return False
    except Exception as e:
        print(f"❌ {description} (Port {port}): ERROR - {e}")
        return False

print("=== IB API Port Check ===")
ports = [
    (7497, "TWS API"),
    (4001, "Gateway API"), 
    (7496, "TWS Demo API"),
    (4002, "Gateway Demo API")
]

open_ports = []
for port, desc in ports:
    if test_port("127.0.0.1", port, desc):
        open_ports.append(port)

if open_ports:
    print(f"\n🎉 Available ports: {open_ports}")
    print(f"Try: market-data test-connection --ib-port {open_ports[0]}")
else:
    print("\n❌ No IB API ports are open.")
    print("Please check IB TWS/Gateway is running and API is enabled.")
