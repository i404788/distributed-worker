from typing import Tuple, Mapping, List, Any
import multiprocessing
from multiprocessing.connection import Listener, Client, Pipe
import select
import time

from .worker import create_worker


default_address = ('localhost', 6000)

class DistributedManager:
  def __init__(self, address:Tuple[str, int]=None, authkey:str=b'secret password', ttl:float=3600.):
    self.address = address or default_address
    self.authkey = authkey
    self.ttl = ttl
    self.listener = Listener(self.address, authkey=self.authkey, backlog=16)
    self.pipes = []
    self.local_processes = []
    self.last_message_time = {}
    self.last_ping = time.time()

  """
  Warning not portable (use Python ~3.7 from anaconda which uses cpython)
  """
  def try_accept(self):
    readable, writable, errored = select.select([self.listener._listener._socket], [], [], .1)
    for s in readable:
      if s is self.listener._listener._socket:
        self.pipes.append(self.listener.accept())
        return True
    return False

  def flush(self):
    for i, pipe in self.get_active_pipes():
      try:
        while pipe.poll():
          self.last_message_time[i] = time.time()
          pipe.recv()
      except EOFError:
        self._on_error(i)
        

  def _is_active(self, worker: int):
    return self.last_message_time.get(worker, 0) + self.ttl > time.time()

  def get_active_pipes(self):
    return [(x, self.pipes[x]) for x in self.get_active_workers()]

  def get_active_workers(self):
    ret = []
    for i, pipe in enumerate(self.pipes):
      last_msg = self.last_message_time.get(i, 0)
      if last_msg + self.ttl > time.time():
        ret.append(i)

    return ret

  def get_unconfirmed_workers(self):
    ret = []
    for i, pipe in enumerate(self.pipes):
      last_msg = self.last_message_time.get(i, -1)
      if last_msg == -1:
        ret.append(i)
    return ret

  def get_dead_workers(self):
    ret = []
    for i, pipe in enumerate(self.pipes):
      last_msg = self.last_message_time.get(i, 0)
      if last_msg + self.ttl < time.time():
        ret.append(i)
    return ret

  def poll(self):
    # Ping every 1/2 TTL
    if self.last_ping + (self.ttl / 2)  < time.time():
      self.fping()

  # broadcast('ping') + Flush
  def fping(self):
    self.broadcast(':ping')
    ready = multiprocessing.connection.wait(self.pipes, timeout=.5)
    self.flush() # Clear all messages (and update last msg time)
    return ready

  # Collects {workeridx: [msg, ...], ...}
  def collect(self) -> Mapping[int, List[Any]]:
    ret = {}
    for i, pipe in enumerate(self.pipes):
      try:
        while pipe.poll():
          recv = pipe.recv()
          ret.setdefault(i, [])
          self.last_message_time[i] = time.time()
          if recv == ':pong' or recv == ':register':
            continue
          ret[i].append(recv)
      except EOFError:
        # If previously active emit error
        if self._is_active(i):
          self._on_error(i)
    
    return ret

  # Spreads {workderidx: [msg, ...] ...}
  def spread(self, obj: Mapping[int, List[Any]]) -> Mapping[int, bool]:
    ret = {}

    if max(obj.keys()) > len(self.pipes):
      raise ValueError('Invalid worker idx %d' % max(obj.keys()))

    for k in obj:
      for msg in obj[k]:
        ret[k] = self.send(k, msg)

    return ret

  def _on_error(self, worker: int):
      wasActive = self._is_active(worker)
      if wasActive:
        self.on_worker_disconnect(worker)
      self.last_message_time[worker] = -1
      return False

  def send(self, worker: int, msg: Any) -> bool:
    try:
      self.pipes[worker].send(msg)
      return True
    except BrokenPipeError:
      self._on_error(worker)
      return False
    

  def broadcast(self, obj: Any) -> List[bool]:
    ret = []
    for pipe in range(len(self.pipes)):
      ret.append(self.send(pipe, obj))
    return ret
  
  # fn = def func(pipe, *args, **kwargs)
  # Create local worker
  def create_local_worker(self, wclass, *args, **kwargs):
    ours, theirs = Pipe()
    self.pipes.append(ours)
    proc = multiprocessing.Process(target=create_worker, args=(theirs, wclass, *args,), kwargs=kwargs)
    self.local_processes.append(proc)
    proc.start()
    self.on_new_worker(len(self.pipes)-1)

  # Can be used as multiprocessing.Client(*args)
  def get_client_args(self):
    return (self.address, 'AF_INET', self.authkey)

  def stop(self):
    self.broadcast(':stop')
    print('Stopping all workers...')
    for i, proc in enumerate(self.local_processes):
      proc.join(10.)
      try:
        proc.close()
      except ValueError as e:
        proc.kill()
        print('Failed to stop local worker %d (PID %d)' % (i, proc.pid))

  def run_once(self):
    self.poll()
    self.loop()

    # Add new workers
    while self.try_accept():
      self.on_new_worker(len(self.pipes)-1)

    # Handle messages
    msgs = self.collect()
    for worker in msgs:
      for msg in msgs[worker]:
        self.handle_msg(worker, msg)

  # User implemented
  def loop(self):
    pass

  # User implemented
  def on_new_worker(self, worker: int):
    pass

  # User implemented
  def on_worker_disconnect(self, worker: int):
    pass

  # User implemented
  def handle_msg(self, worker: int, msg: Any):
    pass

