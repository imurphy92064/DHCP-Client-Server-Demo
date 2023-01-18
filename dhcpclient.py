from socket import *
from uuid import *
from time import time


class Client:
    def __init__(self, ip_address, time_stamp):
        self.mac_address = '00:' + ':'.join(['{:02x}'
                                            .format((getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
        self.ipa = ip_address
        self.ts = time_stamp

    def get_mac_address(self):
        return self.mac_address

    def get_ip_address(self):
        return self.ipa

    def get_time_stamp(self):
        return self.ts

    def set_mac_address(self, new_mac_address):
        self.mac_address = new_mac_address

    def set_ip_address(self, new_ip_address):
        self.ipa = new_ip_address

    def set_time_stamp(self, new_time_stamp):
        self.ts = new_time_stamp


def menu(client_socket, client):
    choice = input(
        'What would you like to do?\n'
        '"release": If the client chose to release, send a RELEASE message to the server,containing its MAC address '
        'and IP address.\n '
        '"renew": If the client chose to renew, send a RENEW message to the server,containing its MAC address and IP '
        'address\n '
        '“quit”: If the client chose to quit, terminate the client’s program. Note that the client does NOT release '
        'its IP address when it quits\n '
        '>>'
    )

    while choice != 'quit':
        if choice == 'release':
            client_socket.send_release(client)
        elif choice == 'renew':
            client_socket.send_renew(client)
        else:
            print('\nPlease Enter "release", "renew" or "quit" to exit the program...')
        choice = input('\n>>')
    exit(0)


class ServerResponse:
    def __init__(self, address, raw_message):
        self.client = address
        self.raw = raw_message.decode()
        self.data = self.raw.splitlines()

    def get_raw(self):
        return self.raw

    def get_type(self):
        return self.data[0]

    def get_mac(self):
        (x, y, raw_mac) = self.data[1].partition(':')  # Cleaning the mac address
        return raw_mac.replace(' ', '')

    def get_ip_address(self):
        (x, y, raw_ipaddr) = self.data[2].partition(':')  # IP Address from the Request Message
        return raw_ipaddr.replace(' ', '')

    def get_time_stamp(self):
        (x, y, raw_time_stamp) = self.data[3].partition(':')  # Time Stamp from the Request Message
        return raw_time_stamp.replace(' ', '')


class ClientSocket:
    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(180)
        self.dest = ('localhost', 12000)

    def send_release(self, client):
        release_msg = f'RELEASE\n' \
                      f"MAC Address: {client.get_mac_address()}\n" \
                      f"IP Address: {client.get_ip_address()}\n" \
                      f"Time Stamp: {client.get_time_stamp()}\n"
        self.socket.sendto(release_msg.encode(), self.dest)

    def send_renew(self, client):
        renew_msg = f'RENEW\n' \
                    f"MAC Address: {client.get_mac_address()}\n" \
                    f"IP Address: {client.get_ip_address()}\n" \
                    f"Time Stamp: {client.get_time_stamp()}\n"
        self.socket.sendto(renew_msg.encode(), self.dest)

    def send_request(self, client):
        renew_msg = f'REQUEST\n' \
                    f"MAC Address: {client.get_mac_address()}\n" \
                    f"IP Address: {client.get_ip_address()}\n" \
                    f"Time Stamp: {client.get_time_stamp()}\n"
        self.socket.sendto(renew_msg.encode(), self.dest)

    def send_discover(self, client):
        initial_message = f'DISCOVER\n' \
                          f'MAC Address: {client.get_mac_address()}\n' \
                          f'IP Address: {client.get_ip_address()}\n' \
                          f'Time Stamp: {client.get_time_stamp()}\n'
        self.socket.sendto(initial_message.encode(), self.dest)  # Discover message sent...

    def receive(self):
        return ServerResponse(self.dest, self.socket.recv(2048))


def main():
    # System's MAC Address
    client = Client('0.0.0.0', 0)
    client_socket = ClientSocket()

    # Sending the Discover Message.
    client_socket.send_discover(client)

    while True:
        response = client_socket.receive()
        print(response.get_raw())

        response_type = response.get_type()
        if response_type == 'OFFER':  # The message is an Offer
            mac_address = response.get_mac()
            # Checking to see if the MAC Address sent back from the server matches system MAC Address
            if mac_address != client.get_mac_address():
                print(f'{mac_address} does not match System MAC Address {client.get_mac_address()}... Exiting')
                exit(0)

            time_stamp = int(response.get_time_stamp())
            if time_stamp < int(time()):
                print('Time Stamp Expired...Exiting')
                exit(0)

            # Send a REQUEST Message
            ip_address = response.get_ip_address()
            client.set_ip_address(ip_address)
            client.set_time_stamp(time_stamp)

            client_socket.send_request(client)
        elif response_type == 'ACKNOWLEDGE':
            mac_address = response.get_mac()
            if mac_address != client.get_mac_address():
                print(f'{mac_address} does not match System MAC Address {client.get_mac_address()}...Exiting')
                exit(0)

            ip_address = response.get_ip_address()
            time_stamp = int(response.get_time_stamp())

            print(f"Your IP Address is {ip_address}\n"
                  f"This address will expire in {time_stamp - int(time())} seconds")

            # setting this clients info
            client.set_ip_address(ip_address)
            client.set_time_stamp(time_stamp)

            menu(client_socket, client)
        elif response_type == 'DECLINE':  # Discovery message was Declined
            print('The server declined discovery... Exiting')
            exit(0)


if __name__ == '__main__':
    main()