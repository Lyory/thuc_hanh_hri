"""Standalone webcam preview; never publishes velocity or gesture commands."""
import argparse
import cv2


def main():
    parser = argparse.ArgumentParser(description='Preview webcam with OpenCV')
    parser.add_argument('--camera-index', type=int, default=0)
    args = parser.parse_args()
    capture = cv2.VideoCapture(args.camera_index, cv2.CAP_V4L2)
    try:
        if not capture.isOpened():
            raise RuntimeError('Cannot open webcam; check camera index and /dev/video*')
        cv2.namedWindow('Webcam preview', cv2.WINDOW_NORMAL)
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError('Cannot read webcam frame')
            cv2.imshow('Webcam preview', cv2.flip(frame, 1))
            cv2.waitKey(1)
            if cv2.getWindowProperty('Webcam preview', cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
