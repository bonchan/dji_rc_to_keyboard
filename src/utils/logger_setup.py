import logging
import os
import sys
from datetime import datetime

# Global variable to persist the session across all calls
_SESSION_ID = None

def setup_logger(obj, worker_name=None):
    global _SESSION_ID
    
    # 1. Automatically determine the name
    # If 'obj' is an instance, use its class name. If it's a string, use the string.
    if worker_name is None:
        worker_name = obj.__class__.__name__ if not isinstance(obj, str) else obj

    # 2. Set the session timestamp once and reuse it
    if _SESSION_ID is None:
        _SESSION_ID = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_file = f"logs/session_{_SESSION_ID}.log"
    logger = logging.getLogger(worker_name)
    
    # Avoid adding handlers if they already exist (prevents duplicate logs)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        f_handler = logging.FileHandler(log_file, encoding='utf-8')
        c_handler = logging.StreamHandler(sys.stdout)
        
        fmt = logging.Formatter('%(asctime)s.%(msecs)03d | %(name)-24s | %(levelname)-8s | %(message)s', 
                                datefmt='%H:%M:%S')
        
        f_handler.setFormatter(fmt)
        c_handler.setFormatter(fmt)

        logger.addHandler(f_handler)
        logger.addHandler(c_handler)

    return logger