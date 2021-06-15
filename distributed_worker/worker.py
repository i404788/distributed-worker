from typing import Tuple, Any, ByteString
import multiprocessing
import time

def run_worker(worker):
  while not worker._done:
    worker.run_once()

def create_worker(pipe, wclass, *args, **kwargs):
  worker = wclass(pipe, *args, **kwargs)
  run_worker(worker)

def create_remote_worker_sync(wclass, client_args: Tuple[Tuple[str, int], str, ByteString], *args, **kwargs):
  pipe = multiprocessing.connection.Client(*client_args)
  create_worker(pipe, wclass, *args, **kwargs)

def create_remote_worker(wclass, client_args: Tuple[Tuple[str, int], str, ByteString], *args, **kwargs):
  spawnf = multiprocessing.Process
  if 'spawnf' in kwargs:
      spawnf = kwargs['spawnf']
      del kwargs['spawnf']
  proc = spawnf(target=create_remote_worker_sync, args=(wclass,client_args, *args), kwargs=kwargs)
  proc.start()
  return proc

# Extend this class
class DistributedWorker:
  def __init__(self, pipe, *args, **kwargs):
    self.pipe = pipe
    self._done = False
    self.pipe.send(':register')
    self.poll_delay = 0.1
  
  def run_once(self):
    stime = time.time()
    self.loop()

    if self.pipe.poll(.1):
      msg = self.pipe.recv()

      if msg == ':stop':
        self._done = True
      elif msg == ':ping':
        self.pipe.send(':pong')
      else:
        self.handle_msg(msg)

    # Delay up until poll_delay is reached (if needed)
    time.sleep(max(stime - time.time() + self.poll_delay, 0))

  def send(self, msg: Any):
    self.pipe.send(msg)

  # User implemented
  def loop(self):
    pass

  # User implemented
  def handle_msg(self, msg: Any):
    pass
