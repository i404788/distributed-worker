# distributed-worker
A Python 3.7 wrapper around multiprocessing for easy cross-machine computation

## What is this?
Distributed Worker is a wrapper around the multiprocessing package allowing you to focus on the distributed computations instead of managing nodes/communication.
You can use regular python primitive to communicate just as in multiprocessing, but you can also use remote machines as workers.

## How does it work?
You create a `DistributedManager` which creates a central server for your workers to connect to.
You can create some logic around it to manage tasks/messages.

Then you implement one or multiple `DistributedWorker`s to handle those tasks.

And now you can run your distributed computations.

## Example Setup
Let's say we want a distributed prime checker, here is a very naive implementation:
```py
def is_prime(x):
  x = float(x)
  for num in range(x):
    if x/num != int(x/num):
      return False
  return True
```

If we want to check a large amount of primes that would take ages, so we want to distribute the task.

First we will create a task server:

```py
from distributed_worker import DistributedManager
def prime_server():
  manager = DistributedManager()

  # Credentials/Endpoint for the workers to use
  print(manager.get_client_args())

  # Tasks left
  pending = list(range(100000))
  # Resulting map
  results = {}
  # Workers that are busy
  tasked = set()

  while len(pending):
    if manager.try_accept():
      print('New worker added')

    # Get list of all active workers (dynamic entry)
    active = set(manager.get_active_workers())

    # Get messages from workers
    msgs = manager.collect()

    # Check all workers/messages
    for worker in msgs:
      for msg in msgs[worker]:
        # Expect result to be {number: isPrimeBool, ...}
        if type(msg) == dict: # to be safe
          for num in msg:
            results[num] = msg[num]
          
          # Mark worker as available for work
          tasked.remove(worker)

    available_workers = active - tasked
    for x in available_workers:
      # Send 100 numbers for processing
      task = pending[:100]
      manager.send(x, task)
      tasked.add(x)
```

Then we'll create a worker:

```py
from distributed_worker import DistributedWorker
class PrimeWorker(DistributedWorker):
  def __init__(self, pipe, *args, **kwargs):
    super().__init__(pipe)
    self.task = []
    self.results = {}

  # Calculations here
  def loop(self):
    # Ideally keep calculations within 1 hour or adjust TTL on the server
    if len(self.task):
      # Tasks available
      ctask = self.task.pop()
      self.results[ctask] = is_prime(ctask)
    else:
      # Finished tasks
      if len(self.results):
        self.send(self.results)
  
  # Messages here
  def handle_msg(self, msg):
    if type(msg) == list:
      self.task = msg
```

Now we can create distributed workers gallore:
```py
from distributed_worker import create_remote_worker
# import PrimeWorker as well

# Example, check console of server
client_args = (('localhost', 6000), 'AF_INET', b'secret password') 

# Create 10 workers (10 threads)
for x in range(10):
  # Add PrimeWorker constructor args if needed
  create_remote_worker(PrimeWorker, client_args)
```

If we just want to utilize our local CPU cores (and not deal with the authentication) we can create workers through the manager:
```py
manager = DistributedManager()
# Again, add PrimeWorker constructor args if needed
manager.create_local_worker(PrimeWorker)
```