# `Peer-to-Peer File Transfer Project`
Computer Networking (CO3093) - Semester 231 - HCMUT

## Overview
A simple peer-to-peer file transfer application using command-shell interpreter. It consists of a server and a client component.

## Requirements 
- Python 3
- PostgreSQL installed on the Server machine, and its library `psycopg2` to connect in python
```
python3 -m pip install psycopg2
```
## Installation
Installation from source is straightforward:
```
$ git clone https://github.com/kuramaa97/CO3093_CN_HK231.git
$ cd CO3093_CN_HK231
```
## Usage
1. Start the central server:
   - Run the `server.py` script to start the central server. Ensure the server is running before proceeding with client actions.

2. Client Setup:
   - Edit the `SERVER_HOST` setting in the `client.py` file to configure the IP for the central server. After that run the `client.py` script to start the client and connect to the central server.

## Features
1. The server has a simple command-shell interpreter
    - `discover hostname`: discover the list of local files of the host named hostname
    - `ping hostname`: live check the host named hostname

2. The client has a simple command-shell interpreter that is used to accept two kinds of commands.
    - `publish lname fname`: a local file (which is stored in the client's file system at lname) is added to the client's repository as a file named fname and this information is conveyed to the server.
    - `fetch fname`: fetch some copy of the target file and add it to the local repository.

## Example
### Server side

```
$ python3 server.py
Server command: 2023-11-26 17:22:42,758 - INFO - Server started and is listening for connections.
2023-11-26 17:22:49,755 - INFO - Received data from ('192.168.1.17', 55460): {"action": "introduce", "hostname": "Lio-PC"}

2023-11-26 17:22:49,755 - INFO - Active connections: 2
2023-11-26 17:22:49,755 - INFO - Connection established with 192.168.1.17 (Lio-PC)

Server command: ping Lio-PC
Host Lio-PC is online.
Server command: discover Lio-PC
Files for Lio-PC: [('vlan.pdf',), ('video.mp4',)]
Server command: 2023-11-26 17:23:19,631 - INFO - Received data from ('192.168.1.17', 55460): 
2023-11-26 17:23:19,632 - INFO - Connection with ('192.168.1.17', 55460) has been closed.

Server command: ping Lio-PC
Host Lio-PC is offline.
```

### Client side

```
python3 client.py
Enter command (publish lname fname, fetch fname, exit): publish Hutao.rar 210.rar
File list updated successfully.
Enter command (publish lname fname, fetch fname, exit): fetch video.mp4
Hosts with the file video.mp4:
Lio-PC at IP 192.168.1.17     
File video.mp4 has been fetched from peer.
```