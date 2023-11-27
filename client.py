import socket
import json
import os
import threading
import shlex


stop_event = threading.Event()

def get_local_files(directory='.'):
    try:
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return files
    except Exception as e:
        return f"Error: Unable to list files - {e}"


def handle_file_request(conn, shared_files_dir):
    try:
        data = conn.recv(4096).decode()
        print(data)
        command = json.loads(data)
        if command['action'] == 'send_file':
            lname = command['lname']
            file_path = os.path.join(shared_files_dir, lname)
            send_file_to_client(conn, file_path)
        elif command['action'] == 'request_file_list':
            files = get_local_files(shared_files_dir)
            response = {'files': files}
            conn.sendall(json.dumps(response).encode() + b'\n')

    finally:
        conn.close()

def send_file_to_client(conn, file_path):
    with open(file_path, 'rb') as f:
        while True:
            bytes_read = f.read(4096)
            if not bytes_read:
                break
            conn.sendall(bytes_read)

def start_host_service(port, shared_files_dir):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('0.0.0.0', port))
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.listen()

    while not stop_event.is_set():
        try:
            server_sock.settimeout(1) 
            conn, addr = server_sock.accept()
            print(f"Accepted connection from {addr}")
            thread = threading.Thread(target=handle_file_request, args=(conn, shared_files_dir))
            thread.start()
        except socket.timeout:
            continue
        except Exception as e:
            break

    server_sock.close()


def publish_file(sock, lname, fname):
    if not os.path.exists(lname):
        print(f"Local file {lname} does not exist.")
        return

    hostname = socket.gethostname()
    command = {
        "action": "publish",
        "fname": fname,
        "lname": lname,
        "hostname": hostname
    }
    sock.sendall(json.dumps(command).encode() + b'\n')
    response = sock.recv(4096).decode()
    print(response)



def fetch_file(sock, fname):
    command = {"action": "fetch", "fname": fname}
    sock.sendall(json.dumps(command).encode() + b'\n')
    response = json.loads(sock.recv(4096).decode())

    if 'addresses' in response:
        hosts = response['addresses']
        host_info_str = "\n".join([f"{host['hostname']} at IP {host['ip']}" for host in hosts])
        print(f"Hosts with the file {fname}:\n{host_info_str}")
        if len(hosts) > 1:
            chosen_ip = input("Enter the IP of the host to download from: ")
            # Find the host entry with the chosen IP to get the corresponding lname
            chosen_host = next((host for host in hosts if host['ip'] == chosen_ip), None)
            if chosen_host:
                request_file_from_peer(chosen_ip, chosen_host['lname'],fname)
            else:
                print("Invalid IP entered.")
        elif hosts:
            chosen_host = hosts[0]
            request_file_from_peer(chosen_host['ip'], chosen_host['lname'],fname)
        else:
            print("No hosts have the file.")
    else:
        print("No peers have the file or the response format is incorrect.")


def request_file_from_peer(ip_address, lname,fname):
    peer_port = 65433  # The port where the peer service is expected to be running
    peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        peer_sock.connect((ip_address, peer_port))
        peer_sock.sendall(json.dumps({'action': 'send_file', 'lname': lname}).encode() + b'\n')
  
        # Proceed with file reception...
   # Assume the peer is sending the file immediately after the request
        with open(fname, 'wb') as f:
            while True:
                data = peer_sock.recv(4096)
                if not data:  # No more data from peer
                    break
                f.write(data)

        peer_sock.close()
        print(f"File {fname} has been fetched from peer.")
    except Exception as e:
        print(f"An error occurred while connecting to peer at {ip_address}:{peer_port} - {e}")
    finally:
        peer_sock.close()




def connect_to_server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    hostname = socket.gethostname()
    sock.sendall(json.dumps({'action': 'introduce', 'hostname': hostname}).encode() + b'\n')

    return sock



def main(server_host, server_port):
    # Start the host service thread
    host_service_thread = threading.Thread(target=start_host_service, args=(65433, './'))
    host_service_thread.start()

    # Connect to the server
    sock = connect_to_server(server_host, server_port)


    try:
        while True:
            user_input = input("Enter command (publish lname fname, fetch fname, exit): ")
            command_parts = shlex.split(user_input)

            if len(command_parts) == 3 and command_parts[0].lower() == 'publish':
                _, lname, fname = command_parts
                publish_file(sock, lname, fname)
            elif len(command_parts) == 2 and command_parts[0].lower() == 'fetch':
                _, fname = command_parts
                fetch_file(sock, fname)
            elif user_input.lower() == 'exit':
                stop_event.set()  # Signal all threads to stop
                sock.close()
                break  # Exit the main loop
            else:
                print("Invalid command.")

    finally:
            sock.close()
            host_service_thread.join()  # Wait for the host service thread to finish


if __name__ == "__main__":
    # 35.221.72.247	
    SERVER_HOST = '35.221.72.247'  # Replace with your server's IP address
    SERVER_PORT = 65432
    main(SERVER_HOST, SERVER_PORT)
