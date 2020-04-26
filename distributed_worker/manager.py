import multiprocessing
from multiprocessing.connection import Listener, Client, Pipe
import select
import time

from .worker import create_worker


default_address = ('localhost', 6000)

class DistributedManager:
  def __init__(self, address=None, authkey=b'secret password', ttl=3600.):
    self.address = address or default_address
    self.authkey = authkey
    self.ttl = ttl
    self.listener = Listener(self.address, authkey=self.authkey, backlog=16)
    self.pipes = []
    self.local_processes = []
    self.last_message_time = {}

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
    for i, pipe in enumerate(self.pipes):
      while pipe.poll():
        self.last_message_time[i] = time.gmtime()
        self.pipes.recv()

  def get_active_workers(self):
    ret = []
    for i, pipe in enumerate(self.pipes):
      last_msg = self.last_message_time.get(i, 0)
      if last_msg + ttl > time.gmtime():
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
      if last_msg + ttl < time.gmtime():
        ret.append(i)

    return ret

  # broadcast('ping') + Flush
  def fping(self):
    self.broadcast(':ping')
    ready = multiprocessing.connection.wait(self.pipes, timeout=.5)
    self.flush() # Clear all messages (and update last msg time)
    return ready

  # Collects {workeridx: [msg, ...], ...}
  def collect(self):
    ret = {}
    for i, pipe in enumerate(self.pipes):
      while pipe.poll():
        ret.setdefault(i, [])
        self.last_message_time[i] = time.gmtime()
        recv = pipe.recv()
        if recv == ':pong' or recv == ':register':
          continue
        ret[i].append(recv)
    
    return ret

  # Spreads {workderidx: [msg, ...] ...}
  def spread(self, obj):
    for k in obj:
      if int(k) > len(self.pipes):
        raise ValueError('Invalid worker idx')

      for msg in obj[k]:
        self.pipes[int(k)].send(msg)

  def send(self, worker, msg):
    self.pipes[worker].send(msg)

  def broadcast(self, obj):
    for pipe in self.pipes:
      pipe.send(obj)
  
  # fn = def func(pipe, *args, **kwargs)
  # Create local worker
  def create_local_worker(self, wclass, *args, **kwargs):
    ours, theirs = Pipe()
    self.pipes.append(ours)
    proc = multiprocessing.Process(target=create_worker, args=(theirs, wclass, *args,), kwargs=kwargs)
    self.local_processes.append(proc)
    proc.start()

  # Can be used as multiprocessing.Client(*args)
  def get_client_args(self):
    return (self.address, 'AF_INET', self.authkey)

  def stop(self):
    self.broadcast('stop')
    print('Stopping all workers...')
    for i, proc in enumerate(self.local_processes):
      proc.join(10.)
      try:
        proc.close()
      except ValueError as e:
        print('Failed to stop local worker %d (PID %d)' % (i, proc.pid))