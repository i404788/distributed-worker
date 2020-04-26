from typing import Tuple, Mapping, List, Any
from distributed_worker import DistributedManager

# def prime_server(manager):
#   # Tasks left
#   pending = list(range(150000))
#   chunks = 1000
#   # Resulting map
#   results = {}
#   # Workers that are busy
#   tasked = set()

#   while len(pending) or tasked:
#     if manager.try_accept():
#       print('New worker added')

#     # Run general manager tasks
#     manager.poll()

#     # Get list of all active workers (dynamically added)
#     active = set(manager.get_active_workers())

#     # Get messages from workers
#     msgs = manager.collect()

#     # Check all workers/messages
#     for worker in msgs:
#       for msg in msgs[worker]:
#         # Expect result to be {number: isPrimeBool, ...}
#         if type(msg) == dict: # to be safe
#           print('Got results from worker %d' % worker)
#           for num in msg:
#             results[num] = msg[num]
          
#           # Mark worker as available for work
#           tasked.remove(worker)

#     available_workers = active - tasked
#     for x in available_workers:
#       if not len(pending):
#         continue
#       chunk = min(len(pending), chunks)
#       # Send chunks (1000) numbers for processing
#       task = pending[:chunk]
#       pending = pending[chunk:]
#       print('Send task %d-%d to worker %d' % (task[0], task[-1], x))
#       manager.send(x, task)
#       tasked.add(x)

#   return results


class PrimeManager(DistributedManager):
  def __init__(self):
    super().__init__()
    self.pending = list(range(150000))
    self.results = {}
    self.tasked = set()
    self.chunks = 1000 # Task size

  def loop(self):
    # No tasks pending, wait on exit
    if len(self.pending) < 1:
        return

    # Assign tasks to workers
    active = set(self.get_active_workers())
    available_workers = active - self.tasked
    for x in available_workers:
      chunk = min(len(self.pending), self.chunks)
      # Send chunks (1000) of numbers for processing
      task = self.pending[:chunk]
      self.pending = self.pending[chunk:]
      print('Send task %d-%d to worker %d' % (task[0], task[-1], x))
      self.send(x, task)
      self.tasked.add(x)

  # User implemented
  def on_new_worker(self, worker: int):
    print('New worker added %d' % worker)

  # User implemented
  def on_worker_disconnect(self, worker: int):
    print('Worker disconnected %d' % worker)

  # User implemented
  def handle_msg(self, worker: int, msg: Any):
    # Worker finished it's task
    for num in msg:
      self.results[num] = msg[num]
    self.tasked.remove(worker)


from distributed_worker import DistributedWorker

def is_prime(x):
  for num in range(2, x):
    if (x % num) == 0:
      return False
  return True

class PrimeWorker(DistributedWorker):
  def __init__(self, pipe, *args, **kwargs):
    super().__init__(pipe)
    self.task = []
    self.results = {}

  # Calculations here
  def loop(self):
    # Ideally keep the executing here within 1 hour or adjust TTL on the server
    if len(self.task):
      # Tasks available
      ctask = self.task.pop()
      self.results[ctask] = is_prime(ctask)
    else:
      # Finished tasks
      if len(self.results):
        print('Sending results to manager')
        self.send(self.results)
        # Clear results so we don't resend
        self.results = {}
  
  # Messages here
  def handle_msg(self, msg):
    if type(msg) == list:
      print('Got task from manager %d-%d' % (msg[0], msg[-1]))
      self.task = msg


if __name__ == "__main__":
    manager = PrimeManager()

    for x in range(5):
      manager.create_local_worker(PrimeWorker)

    # For adding remote workers
    print('client creds:', manager.get_client_args())

    while manager.tasked or manager.pending:
      manager.run_once()
      # Can do other tasks here as well

    # Print the results
    for x in manager.results:
      if manager.results[x]:
        print(x)

    manager.stop()