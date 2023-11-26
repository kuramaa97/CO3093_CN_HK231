import logging
import socket
import threading
import json
import psycopg2
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(dbname="MMT", user="postgres", password="061203", host="localhost", port="4000")
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

def client_handler(conn, addr):
    try:

        while True:
            data = conn.recv(4096).decode()
            log_event(f"Received data from {addr}: {data}")
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


    except Exception as e:
        logging.exception(f"An error occurred while handling client {addr}: {e}")
    finally:
        if client_hostname:
            del active_connections[client_hostname]  
        conn.close()
        log_event(f"Connection with {addr} has been closed.")

def server_command_shell():
    while True:
        cmd_input = input("Server command: ")
        cmd_parts = cmd_input.split()
        if cmd_parts:
            action = cmd_parts[0]
            if action == "discover" and len(cmd_parts) == 2:
                hostname = cmd_parts[1]
                cur.execute("SELECT fname FROM client_files WHERE hostname = %s", (hostname,))
                files = cur.fetchall()
                print(f"Files for {hostname}: {files}")
            elif action == "ping" and len(cmd_parts) == 2:
                hostname = cmd_parts[1]
                is_online = hostname in active_connections
                status = 'online' if is_online else 'offline'
                print(f"Host {hostname} is {status}.")
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
    # You would have some mechanism to properly shutdown the server here
    # This could involve setting a shutdown flag that your threads check,
    # or closing server sockets, etc.
    sys.exit(0)