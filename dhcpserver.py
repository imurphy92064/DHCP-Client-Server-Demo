from socket import *
from time import time


class Record:
    def __init__(self, record_number, mac_address, ip_address, time_stamp, acknowledged=False):
        self.rn = record_number
        self.maca = mac_address
        self.ipa = ip_address
        self.ts = time_stamp
        self.ack = acknowledged

    def is_expired(self):
        return self.ts < int(time())

    def get_record_number(self):
        return self.rn

    def get_mac_address(self):
        return self.maca

    def get_ip_address(self):
        return self.ipa

    def get_time_stamp(self):
        return self.ts

    def get_acknowledge(self):
        return self.ack


class RecordManager:
    def __init__(self, network_id, subnet_mask, expire_time):
        self.addresses = []
        net_id = RecordManager.__ip_to_numb(network_id)
        mask = RecordManager.__ip_to_numb(subnet_mask)

        current_ip = net_id + 1
        while (current_ip & mask) == net_id:  # while ip is in the network
            self.addresses.append(RecordManager.__ip_numb_to_str(current_ip))
            current_ip += 1
        self.addresses.pop()  # Remove last IP (broadcast)

        self.expire_time = expire_time
        self.records = []

    @staticmethod
    def __ip_numb_to_str(ip):
        first = ip >> 24 & 0xFF
        second = ip >> 16 & 0xFF
        third = ip >> 8 & 0xFF
        fourth = ip & 0xFF
        return "{}.{}.{}.{}".format(first, second, third, fourth)

    @staticmethod
    def __ip_to_numb(ip):
        parts = ip.strip().split('.')
        assert len(parts) == 4
        numb = 0
        numb |= int(parts[3])
        numb |= int(parts[2]) << 8
        numb |= int(parts[1]) << 16
        numb |= int(parts[0]) << 24
        return numb

    def find_by_mac(self, mac_address):
        for rec in self.records:
            if rec.get_mac_address() == mac_address:
                return rec
        return None

    def print(self):
        for rec in self.records:
            print(f"Record Number: {rec.get_record_number()}\nMAC Address: {rec.get_mac_address()}\nIP Address: "
                  f"{rec.get_ip_address()}\nTime Stamp: {rec.get_time_stamp()}\nAcknowledge: {rec.get_acknowledge()}\n")

    def add_to_pool(self, socket_manager, mac_address, client_addr):
        if len(self.records) >= len(self.addresses):
            expired = self.find_expired_record()
            if expired is None:  # none are expired, no room for new client
                socket_manager.send_decline(client_addr)
            else:  # reassign expired IP address
                expired.maca = mac_address
                expired.ts = time() + self.expire_time
                expired.ack = False
                print('Updated Record:')
                print(f'Record Number: {expired.get_record_number()}\nMAC Address: {expired.get_mac_address()}\n'
                      f'IP Address: {expired.get_ip_address()}\nTime Stamp: {expired.get_time_stamp()}\n'
                      f'Acknowledge: {expired.get_acknowledge()}\n')
                socket_manager.send_offer(expired, client_addr)
        else:  # we have room to add
            new_record = Record(len(self.records) + 1, mac_address, self.addresses[len(self.records)],
                                int(time()) + self.expire_time, False)
            self.records.append(new_record)
            print('New Record:')
            print(f'Record Number: {new_record.get_record_number()}\nMAC Address: {new_record.get_mac_address()}\n'
                  f'IP Address: {new_record.get_ip_address()}\nTime Stamp: {new_record.get_time_stamp()}\n'
                  f'Acknowledge: {new_record.get_acknowledge()}\n')
            socket_manager.send_offer(new_record, client_addr)

    def find_expired_record(self):
        for rec in self.records:
            if rec.is_expired():
                return rec
        return None

    def renew(self, record):
        record.ts = int(time()) + self.expire_time


class ClientResponse:
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

    def get_time_stamp(self):
        (x, y, raw_time_stamp) = self.data[3].partition(':')  # Time Stamp from the Request Message
        return raw_time_stamp.replace(' ', '')

    def get_ip_address(self):
        (x, y, raw_ipaddr) = self.data[2].partition(':')  # IP Address from the Request Message
        return raw_ipaddr.replace(' ', '')


class SocketManager:
    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', 12000))
        self.socket.settimeout(60)  # 1 minute timeout for the socket

    def send_offer(self, client_record, address):
        offer_msg = f'OFFER\n' \
                    f'MAC Address: {client_record.get_mac_address()}\n' \
                    f'IP Address: {client_record.get_ip_address()}\n' \
                    f'Time Stamp: {client_record.get_time_stamp()}\n'
        self.socket.sendto(offer_msg.encode(), address)

    def send_acknowledge(self, client_record, address):
        client_record.ack = True
        acknowledge_msg = f"ACKNOWLEDGE\n" \
                          f"MAC Address: {client_record.get_mac_address()}\n" \
                          f"IP Address: {client_record.get_ip_address()}\n" \
                          f"Time Stamp: {client_record.get_time_stamp()}\n"
        self.socket.sendto(acknowledge_msg.encode(), address)

    def send_decline(self, address):
        decline_msg = f'DECLINE\n' \
                      f'Server Declined your Message\n'
        self.socket.sendto(decline_msg.encode(), address)

    def receive(self):
        raw_message, curr_client = self.socket.recvfrom(2048)
        return ClientResponse(curr_client, raw_message)

    def send_list(self, record_manager, address):
        list_msg = ""
        for rec in record_manager.records:
            list_msg += f'mac: {rec.get_mac_address()} | ip: {rec.get_ip_address()} ' \
                        f'| num: {rec.get_record_number()} | time: {rec.get_time_stamp()} ' \
                        f'| ack: {rec.get_acknowledge()}\n'
        self.socket.sendto(list_msg.encode(), address)


def main():
    print('Starting server...')

    socket_manager = SocketManager()
    record_manager = RecordManager('192.168.45.0', '255.255.255.240', 60)  # 60 second record expire time
    while True:
        print('\nServer Ready to Receive Messages...')
        resp = socket_manager.receive()

        resp_type = resp.get_type()
        if resp_type == 'DISCOVER':  # Discover message received
            print(resp.get_raw())

            mac_address = resp.get_mac()
            rec = record_manager.find_by_mac(mac_address)
            if rec is not None:
                if rec.is_expired():
                    record_manager.renew(rec)
                    socket_manager.send_offer(rec, resp.client)
                else:
                    socket_manager.send_acknowledge(rec, resp.client)
            else:  # record not in our list
                record_manager.add_to_pool(socket_manager, mac_address, resp.client)
        elif resp_type == 'REQUEST':  # Request message received
            print(resp.get_raw())

            mac_address = resp.get_mac()
            rec = record_manager.find_by_mac(mac_address)
            if rec is None:
                socket_manager.send_decline(resp.client)
                continue

            if not rec.get_ip_address() == resp.get_ip_address():
                socket_manager.send_decline(resp.client)
                continue

            time_stamp = resp.get_time_stamp()
            if rec.is_expired() or int(time_stamp) != rec.ts:  # Timestamp too old or mismatch
                socket_manager.send_decline(resp.client)
                continue

            rec.ack = True
            socket_manager.send_acknowledge(rec, resp.client)
        elif resp_type == 'RELEASE':
            print(resp.get_raw())

            mac_address = resp.get_mac()
            rec = record_manager.find_by_mac(mac_address)
            if rec is not None:
                rec.ts = int(time())
                rec.ack = False
        elif resp_type == 'RENEW':
            print(resp.get_raw())

            mac_address = resp.get_mac()
            record = record_manager.find_by_mac(mac_address)
            if record is not None:
                record_manager.renew(record)
                record.ack = True
                socket_manager.send_acknowledge(record, resp.client)
            else:
                record_manager.add_to_pool(socket_manager, mac_address, resp.client)
        elif resp_type == 'LIST':
            print(resp.get_raw())
            socket_manager.send_list(record_manager, resp.client)


if __name__ == "__main__":
    main()
