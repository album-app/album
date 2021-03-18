import socket
import sys

HOST = "localhost"
PORT = 8081

if __name__ == "__main__":
    clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientsocket.connect((HOST, PORT))

    for arg in sys.argv[1:]:
        clientsocket.sendall(arg.encode("utf-8") + b'\x00')
