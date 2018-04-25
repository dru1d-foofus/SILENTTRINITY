import argparse


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', nargs=1, help='IP to bind to')
    parser.add_argument('server_password', nargs=1, help='Server password')
    parser.add_argument('-p', '--port', default=5000, type=int, help='Port to bind to')
    args = parser.parse_args()

    args.ip = args.ip[0]
    args.server_password = args.server_password[0]

    return args
