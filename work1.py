import time
import sys


for i in range(50):
    sys.stdout.write(f'Line {i}\n')
    sys.stdout.flush()  # necessary to really stream output for some reason, print() not sufficient
    time.sleep(0.1)
