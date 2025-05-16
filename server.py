import os
import datetime
from reliable_udp import ReliableUDP

# splits the request into method, path, headers, and body
def parse_http_request(request):
    lines = request.strip().split('\r\n')
    request_line = lines[0]
    method, path, _ = request_line.split()
    headers = {}
    body = ''
    i = 1
    while i < len(lines) and lines[i]:
        key, value = lines[i].split(': ', 1)
        headers[key] = value
        i += 1
    if i + 1 < len(lines):
        body = '\r\n'.join(lines[i+1:])
    return method, path, headers, body

def build_http_response(status_code, body, content_type='text/plain'):
    reason_phrases = {
        200: 'OK',
        400: 'Bad Request',
        404: 'Not Found'
    }
    reason = reason_phrases.get(status_code, 'Unknown')
    current_date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    response_lines = [
        f'HTTP/1.0 {status_code} {reason}',
        f'Date: {current_date}',
        'Server: CustomUDPServer/1.0',
        f'Content-Type: {content_type}; charset=utf-8',
        f'Content-Length: {len(body)}',
        'Connection: close',
        '',
        body
    ]
    return '\r\n'.join(response_lines)


def main():
    ip = '127.0.0.1'
    port = 8080
    server = ReliableUDP(ip, port)
    server.set_debug_mode(True)
    print(f"Server is running...on IP Address = {ip} and port Number = {port}")

    while True:
        if server.accept_connection():
            print("Connection accepted.")
            while server.connected:
                data = server.receive()
                if data:
                    method, path, headers, body = parse_http_request(data)
                    if method == 'GET':
                        file_path = path.strip('/')
                        if os.path.exists(file_path):
                            with open(file_path, 'r') as f:
                                content = f.read()
                            # Check if it's an HTML file
                            if file_path.endswith('.html'):
                                content_type = 'text/html'
                            else:
                                content_type = 'text/plain'
                            response = build_http_response(200, content, content_type)
                        else:
                            response = build_http_response(404, 'File not found.')

                    elif method == 'POST':
                        # Wrap the POST body in HTML tags
                        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>POST Response</title>
</head>
<body>
    <h1>Data Received</h1>
    <p>{body}</p>
</body>
</html>"""

                        # Save it to an HTML file
                        with open('post_data.html', 'w') as f:
                            f.write(html_content)

                        # Send the HTML content as a response
                        response = build_http_response(200, html_content, content_type='text/html')

                    else:
                        response = build_http_response(400, 'Bad Request.')
                    server.send(response)
                else:
                    break
            server.close_connection()

if __name__ == '__main__':
    main()
