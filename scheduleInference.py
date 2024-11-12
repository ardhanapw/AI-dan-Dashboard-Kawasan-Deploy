import os
import time
from datetime import datetime
import subprocess

INFERENCE_FILE_PATH = os.getcwd() + "\main.py"
PYTHON_PATH = '.venv/Scripts/python.exe' if os.path.exists(os.getcwd() + '\.venv') else 'python'

def startInference():
    return subprocess.Popen([PYTHON_PATH, INFERENCE_FILE_PATH])

def terminateInference(process):
    process.terminate()
    try:
        process.wait(timeout = 10)
    except subprocess.TimeoutExpired:
        process.kill()

def restartInference():
    inference = startInference()
    
    while True:
        now = datetime.now().time()
        time.sleep(1)
        if now.strftime("%H:%M:%S") == "23:59:56":
            terminateInference(inference)
            time.sleep(1)
            inference = startInference()
    
restartInference()
