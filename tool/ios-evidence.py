"""Extract one bounded public simulator PNG from native GitHub job logs."""
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re

MAX_PNG = 6 * 1024 * 1024
MAX_LOG = 128 * 1024 * 1024
MAX_LINE = 4096
MARKER = 'STORE_AUTOMATION_PNG_'


def extract(logs, output):
    """Validate everything before exclusive output creation; never execute log text."""
    state, data, total = 'BEFORE', bytearray(), 0
    expected_size = expected_hash = None
    padded = False
    with Path(logs).open('rb') as stream:
        while True:
            line = stream.readline(MAX_LINE + 1)
            if not line:
                break
            total += len(line)
            if len(line) > MAX_LINE or total > MAX_LOG:
                raise ValueError('Log exceeds bounded line/file limits')
            index = line.find(MARKER.encode())
            # GitHub also echoes the shell/Python script; marker literals are not output records.
            if index > 0 and not re.fullmatch(
                    rb'(?:[^\r\n]*\t)?\d{4}-\d{2}-\d{2}T[0-9:.]+Z ', line[:index]):
                index = -1
            if index < 0:
                if state == 'DATA':
                    raise ValueError('Unexpected non-data line inside screenshot block')
                continue
            try:
                record = line[index:].decode('ascii').rstrip('\r\n')
            except UnicodeDecodeError as error:
                raise ValueError('Screenshot marker must be ASCII') from error
            begin = re.fullmatch(MARKER + r'BEGIN launch ([0-9]+) ([a-f0-9]{64})', record)
            if begin:
                if state != 'BEFORE':
                    raise ValueError('Duplicate or nested screenshot block')
                expected_size, expected_hash = int(begin[1]), begin[2]
                if not 0 < expected_size <= MAX_PNG:
                    raise ValueError('Screenshot size exceeds limit or is empty')
                state = 'DATA'
            elif record.startswith(MARKER + 'DATA '):
                if state != 'DATA' or padded:
                    raise ValueError('Unexpected screenshot data or data after base64 padding')
                chunk = record[len(MARKER + 'DATA '):]
                if not chunk:
                    raise ValueError('Empty screenshot data')
                try:
                    decoded = base64.b64decode(chunk, validate=True)
                except (ValueError, binascii.Error) as error:
                    raise ValueError('Invalid base64 screenshot data') from error
                if len(data) + len(decoded) > expected_size:
                    raise ValueError('Screenshot data exceeds declared size')
                data.extend(decoded)
                padded = '=' in chunk
            elif record == MARKER + 'END launch':
                if state != 'DATA':
                    raise ValueError('Unexpected or duplicate screenshot end')
                state = 'AFTER'
            else:
                raise ValueError('Malformed screenshot marker')
    if state != 'AFTER':
        raise ValueError('Missing or unterminated screenshot block')
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != expected_size or digest != expected_hash:
        raise ValueError('Screenshot size/hash mismatch')
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Screenshot has no PNG signature')
    # No directories, existing output or symlink targets are overwritten.
    with Path(output).open('xb') as stream:
        stream.write(data)
    return {'output': str(Path(output).absolute()), 'bytes': len(data), 'sha256': digest,
            'source': 'selected local GitHub log', 'remote_provenance_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', type=Path)
    parser.add_argument('png', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(extract(args.logs, args.png), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
