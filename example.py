from distributed_worker import DistributedManager

def create_worker(pipe):
  worker = ESWorker(pipe)

  while not worker.done:
    worker.loop()

class ESWorker:
  def __init__(self, pipe, **kwargs):
    self.pipe = pipe
    self.done = False

  
  def loop(self):
    if not pipe.poll(10):
      return

    msg = pipe.recv()

    if msg == 'stop':
      self.done = True
    elif msg == 'ping':
      pipe.send('pong')
    else:
      self.handle_msg(msg)

  def handle_msg(self, msg):
    pass

if __name__ == "__main__":
    manager = DistributedManager()
    print(manager.try_accept())
    print(manager.get_client_args())