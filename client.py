from reliable_udp import ReliableUDP
import datetime

def build_http_request(method, path, host, body=''):
    current_date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    headers = [
        f'{method} {path} HTTP/1.0',
        f'Host: {host}',
        f'Date: {current_date}',
        'User-Agent: CustomUDPClient/1.0',
        'Accept: */*',
        'Connection: close'
    ]

    if method == 'POST':
        headers.append('Content-Type: text/plain; charset=utf-8')
        headers.append(f'Content-Length: {len(body)}')

    headers.append('')  # empty line before body
    headers.append(body)

    return '\r\n'.join(headers)

def main():
    client = ReliableUDP('127.0.0.1', 9090, '127.0.0.1', 8080)
    client.set_debug_mode(True)

    if not client.establish_connection():
        print("Failed to connect to server.")
        return

    print("Connection established.")
    method = input("Enter method (GET or POST): ").strip().upper()

    if method not in ['GET', 'POST']:
        print("Unsupported method.")
        client.close_connection()
        client.close()
        return

    if method == 'GET':
        path = input("Enter path: ").strip()
        request = build_http_request('GET', path, 'localhost')
    else:
        path = '/'
        body = input("Enter data to POST: ")
        request = build_http_request('POST', path, 'localhost', body)

    client.send(request)
    response = client.receive()

    if response:
        print("\nResponse from server:\n")
        print(response)

    client.close_connection()
    client.close()

if __name__ == '__main__':
    main()
