import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Or "sync" if gevent causes issues with your async code
timeout = 120
keepalive = 5

accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stdout
loglevel = "info"

capture_output = True
enable_stdio_inheritance = True
