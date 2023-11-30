import logging
import socket
import threading
import json
import psycopg2
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(dbname="", user="postgres", password="", host="", port="5432")
cur = conn.cursor()

def log_event(message):
    logging.info(message)

def update_client_info(hostname, addr, fname, lname):
    # Update the client's file list in the database
    cur.execute(
        "INSERT INTO client_files (lname, fname, hostname, address) VALUES (%s, %s, %s, %s) ON CONFLICT (address, fname, hostname) DO UPDATE SET lname = EXCLUDED.lname",
        (lname, fname, hostname, addr)
    )
    conn.commit()

active_connections = {}  
host_files = {}

def client_handler(conn, addr):
    try:

        while True:
            data = conn.recv(4096).decode()
            # log_event(f"Received data from {addr}: {data}")
            if not data:
                break

            command = json.loads(data)

            if command.get('action') == 'introduce':
                client_hostname = command.get('hostname')
                active_connections[client_hostname] = conn
                log_event(f"Connection established with {addr[0]} ({client_hostname})")

            elif command['action'] == 'publish':
                hostname = command['hostname']
                fname = command['fname']
                lname= command['lname']
                log_event(f"Updating client info in database for hostname: {hostname}")
                update_client_info(hostname, addr[0], fname, lname)  # addr[0] is the IP address
                log_event(f"Database update complete for hostname: {hostname}")
                conn.sendall("File list updated successfully.".encode())

            elif command['action'] == 'fetch':
                fname = command['fname']
                # Query the database for the IP addresses of the clients that have the file
                cur.execute("SELECT DISTINCT ON (address, hostname, fname)   address, hostname, lname FROM client_files WHERE fname = %s", (fname,))
                results = cur.fetchall()
                if results:
                    # Create a list of dictionaries with 'hostname' and 'ip' keys
                    peers_info = [{'hostname': hostname, 'ip': address, 'lname': lname} for address, hostname, lname in results if hostname in active_connections]
                    conn.sendall(json.dumps({'addresses': peers_info}).encode())
                else:
                    conn.sendall(json.dumps({'error': 'File not available'}).encode())

            elif command['action'] == 'file_list':
                files = command['files']
                print(f"List of files : {files}")

    except Exception as e:
        logging.exception(f"An error occurred while handling client {addr}: {e}")
    finally:
        if client_hostname:
            del active_connections[client_hostname]  
        conn.close()
        log_event(f"Connection with {addr} has been closed.")

def request_file_list_from_client(hostname):
    if hostname in active_connections:
        conn = active_connections[hostname]
        print(active_connections[hostname])
        ip_address, _ = conn.getpeername()
        # print(ip_address)
        peer_port = 65433  
        peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_sock.connect((ip_address, peer_port))
        request = {'action': 'request_file_list'}
        peer_sock.sendall(json.dumps(request).encode() + b'\n')
        response = json.loads(peer_sock.recv(4096).decode())
        print(response)
        peer_sock.close()
        if 'files' in response:
            return response['files']
        else:
            return "Error: No file list in response"
    else:
        return "Error: Client not connected"

def discover_files(hostname):
    # Connect to the client and request the file list
    files = request_file_list_from_client(hostname)
    print(f"Files on {hostname}: {files}")

def ping_host(hostname):
    cur.execute("SELECT address FROM client_files WHERE hostname = %s", (hostname,))
    results = cur.fetchone()  
    ip_address = results[0]
    print(ip_address)
    if ip_address:
        peer_port = 65433
        peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_sock.connect((ip_address, peer_port))
        request = {'action': 'ping'}
        peer_sock.sendall(json.dumps(request).encode() + b'\n')
        response = peer_sock.recv(4096).decode()
        print(response)
        peer_sock.close()
        if response:
            print(f"{hostname} is online!")
        else:
            print(f"{hostname} is offline!")
    else:
        print("There is no host with that name")



def server_command_shell():
    while True:
        cmd_input = input("Server command: ")
        cmd_parts = cmd_input.split()
        if cmd_parts:
            action = cmd_parts[0]
            if action == "discover" and len(cmd_parts) == 2:
                hostname = cmd_parts[1]
                thread = threading.Thread(target=discover_files, args=(hostname,))
                thread.start()
            elif action == "ping" and len(cmd_parts) == 2:
                hostname = cmd_parts[1]
                thread = threading.Thread(target=ping_host, args=(hostname,))
                thread.start()
            elif action == "exit":
                break
            else:
                print("Unknown command or incorrect usage.")

def start_server(host='0.0.0.0', port=65432):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    log_event("Server started and is listening for connections.")

    try:
        while True:
            conn, addr = server_socket.accept()
            # host = server_socket.getsockname()
            # log_event(f"Accepted connection from {addr}, hostname is {host}")
            thread = threading.Thread(target=client_handler, args=(conn, addr))
            thread.start()
            log_event(f"Active connections: {threading.active_count() - 1}")
    except KeyboardInterrupt:
        log_event("Server shutdown requested.")
    finally:
        server_socket.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    # Start the server command shell in the main thread
    server_command_shell()

    # Signal the server to shutdown
    print("Server shutdown requested.")
    
    sys.exit(0)