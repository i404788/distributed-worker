from typing import Tuple, Any, ByteString
import multiprocessing

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
  proc = multiprocessing.Process(target=create_remote_worker_sync, args=(wclass,client_args, *args), kwargs=kwargs)
  proc.start()
  return proc

# Extend this class
class DistributedWorker:
  def __init__(self, pipe, *args, **kwargs):
    self.pipe = pipe
    self._done = False
    self.pipe.send(':register')
  
  def run_once(self):
    self.loop()

    if self.pipe.poll():
      msg = self.pipe.recv()

      if msg == ':stop':
        self._done = True
      elif msg == ':ping':
        self.pipe.send(':pong')
      else:
        self.handle_msg(msg)

  def send(self, msg: Any):
    self.pipe.send(msg)

  # User implemented
  def loop(self):
    pass

  # User implemented
  def handle_msg(self, msg: Any):
    pass
