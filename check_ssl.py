#!/usr/bin/env python3
"""
Copyright 2020 Holger Mueller

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public License
as published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.
You should have received a copy of the GNU Lesser General Public
License along with this program. If not, see
<http://www.gnu.org/licenses/>.
"""

import sys
import socket
from datetime import datetime
from typing import List

from OpenSSL import SSL

__version__ = "0.2"

TIMEOUT = 10  # socket timeout

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3


def get_server_cert(host: str, port: int = 443, ipv6: bool = False,
                    sni_host: str = "", timeout: int = TIMEOUT) -> SSL.X509:
    if ipv6:
        ip_version = socket.AF_INET6
    else:
        ip_version = socket.AF_INET

    ctx = SSL.Context(SSL.SSLv23_METHOD)

    sock = socket.socket(ip_version, socket.SOCK_STREAM)
    sock = SSL.Connection(ctx, sock)

    if sni_host != "":
        sock.set_tlsext_host_name(sni_host.encode())

    sock.settimeout(timeout)
    sock.connect((host, port))
    sock.setblocking(1)
    sock.do_handshake()

    x509 = sock.get_peer_certificate()

    sock.shutdown()
    sock.close()

    return x509


def format_x509_name(x509name: SSL.X509Name) -> str:
    return "\n".join([
        f"{comp[0].decode('utf-8')}={comp[1].decode('utf-8')}"
        for comp in x509name.get_components()
    ])


def format_x509(cert: SSL.X509) -> str:
    res = (
        f"Subject:\n{format_x509_name(cert.get_subject())}\n"
        f"{'=' * 72}\n"
        f"Issuer:\n{format_x509_name(cert.get_issuer())}\n"
        f"{'=' * 72}\n"
    )
    for idx in range(cert.get_extension_count()):
        ext = cert.get_extension(idx)
        res += (
            f"{ext.get_short_name().decode('utf-8')}: {ext}\n"
            f"{'-' * 72}\n"
        )
    res += f"Not before: {cert.get_notBefore().decode('utf-8')}\n"
    res += f"Not after:  {cert.get_notAfter().decode('utf-8')}\n"

    return res

def get_subject_alt_names(cert: SSL.X509) -> List[str]:
    raw_names = ""
    names = []
    for idx in range(cert.get_extension_count()):
        ext = cert.get_extension(idx)
        if ext.get_short_name().decode("utf-8") == 'subjectAltName':
            raw_names += str(ext) + ", "
    for name in raw_names.split(', '):
        if name.startswith('DNS:'):
            names.append(name[4:])
    return names


def check_hostname(cert: SSL.X509, hostname: str, use_subject: bool = False,
                   allow_wildcard: bool = False) -> bool:
    if use_subject:
        subject = cert.get_subject()
        names = [
            c[1].decode("utf-8") for c in subject.get_components()
            if c[0].decode("utf-8") == "CN"
        ]
    else:
        names = get_subject_alt_names(cert)
    if allow_wildcard:
        hostname = hostname.split('.', 1)[1]  # remove hostpart from hostname
        names = [n.lstrip('*.') for n in names]
    return hostname in names


#
# Main program
#
def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    parser.add_argument("-d", "--debug", action="store_true",
                        help="deliver debugging output")
    parser.add_argument("-H", "--host", required=True,
                        help="host to connect to")
    parser.add_argument("-p", "--port", type=int, default=443,
                        help="port to connect to")
    parser.add_argument("-6", "--ipv6", action="store_true",
                        help="use ipv6")
    parser.add_argument("-s", "--sni", default="",
                        help="use sni name")
    parser.add_argument("-w", "--warning", type=int, default=31,
                        help="warn if certificate is valid for less than"
                        " WARNING days. (default: 31)")
    parser.add_argument("-c", "--critical", type=int, default=14,
                        help="crictical if certificate is valid for less than"
                        " CRITICAL days. (default: 14)")
    parser.add_argument("-C", "--compareCN", action="store_true",
                        help="check hostname against CN (deprecated)")
    parser.add_argument("-W", "--wildcard", action="store_true",
                        help="allow wildcard certs")
    parser.add_argument("-t", "--timeout", type=int, default=TIMEOUT,
                        help="socket timeout in seconds. (default: 10)")
    args = parser.parse_args()

    try:
        x509 = get_server_cert(args.host, args.port,
                               args.ipv6, args.sni, args.timeout)
    except socket.gaierror as err:
        sys.stdout.write(f"CRITICAL: {err}\n")
        sys.exit(STATE_CRITICAL)
    except socket.timeout:
        sys.stdout.write("CRITICAL: Timeout on connect")
        sys.exit(STATE_CRITICAL)

    if args.debug:
        print(format_x509(x509))

    if args.sni != "":
        hostname = args.sni
    else:
        hostname = args.host

    if not check_hostname(x509, hostname, args.compareCN, args.wildcard):
        sys.stdout.write("CRITICAL: Certificate name missmatch\n")
        sys.exit(STATE_CRITICAL)

    now = datetime.utcnow()

    not_before = datetime.strptime(
        x509.get_notBefore().decode('utf-8'),
        r"%Y%m%d%H%M%SZ")
    if now < not_before:
        sys.stdout.write(
            f"CRITICAL: Certificate not yet valid ({not_before})\n")
        sys.exit(STATE_CRITICAL)

    not_after = datetime.strptime(
        x509.get_notAfter().decode('utf-8'),
        r"%Y%m%d%H%M%SZ")
    valid_td = not_after - now
    if valid_td.days < args.critical:
        sys.stdout.write(
            f"CRITICAL: Certificate only valid for {valid_td.days} days."
            f" ({not_after})\n")
        sys.exit(STATE_CRITICAL)
    if valid_td.days < args.warning:
        sys.stdout.write(
            f"WARNING: Certificate only valid for {valid_td.days} days."
            f" ({not_after})\n")
        sys.exit(STATE_WARNING)
    sys.stdout.write(
        f"OK: Certificate valid for {valid_td.days} days."
        f" ({not_after})\n")
    sys.exit(STATE_OK)


if __name__ == '__main__':
    import argparse
    main()
