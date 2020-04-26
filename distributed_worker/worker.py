import multiprocessing

def run_worker(worker):
  while not worker.done:
    worker.loop()

def create_worker(pipe, wclass, *args, **kwargs):
  worker = wclass(pipe, *args, **kwargs)
  run_worker(worker)

def create_remote_worker_sync(wclass, client_args, *args, **kwargs):
  pipe = multiprocessing.connection.Client(*client_args)
  create_worker(pipe, wclass, *args, **kwargs)

def create_remote_worker(wclass, client_args, *args, **kwargs):
  proc = multiprocessing.Process(target=create_remote_worker_sync, args=(wclass,client_args, *args), kwargs=kwargs)
  proc.start()
  return proc

# Extend this class
class DistributedWorker:
  def __init__(self, pipe, *args, **kwargs):
    self.pipe = pipe
    self._done = False
    self.pipe.send(':register')
  
  def _run_loop(self):
    if not pipe.poll(10):
      return

    msg = pipe.recv()

    if msg == ':stop':
      self._done = True
    elif msg == ':ping':
      pipe.send(':pong')
    else:
      self.handle_msg(msg)

    self.loop()

  def send(self, msg):
    self.pipe.send(msg)

  # User implemented
  def loop(self):
    pass

  # User implemented
  def handle_msg(self, msg):
    pass
