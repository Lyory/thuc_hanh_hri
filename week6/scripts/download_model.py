#!/usr/bin/env python3
"""Download the official, versioned MediaPipe model before building the package."""
from pathlib import Path
import hashlib
import urllib.request
import zipfile

URL = ('https://storage.googleapis.com/mediapipe-models/gesture_recognizer/'
       'gesture_recognizer/float16/1/gesture_recognizer.task')
TARGET = (Path(__file__).resolve().parents[1] / 'src/turtlebot4_gesture_control'
          / 'models/gesture_recognizer.task')
SHA256 = '97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482'


def valid_model(path):
    return (path.is_file() and zipfile.is_zipfile(path)
            and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256)


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if valid_model(TARGET):
        print(f'Model already available: {TARGET}')
        return
    temporary = TARGET.with_suffix('.download')
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if not valid_model(temporary):
            raise RuntimeError('Downloaded model failed ZIP / SHA256 validation')
        temporary.replace(TARGET)
        print(f'Model saved: {TARGET}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
