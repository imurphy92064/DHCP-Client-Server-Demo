from socket import *


def main():
    sock = socket(AF_INET, SOCK_DGRAM)

    print("Sending LIST request to DHCP server")
    sock.sendto("LIST".encode(), ('localhost', 12000))

    resp = sock.recv(2048)
    records = resp.decode().splitlines()

    print("All records:")
    for record in records:
        print(record)

    sock.close()


if __name__ == "__main__":
    main()


