distributed-worker
==================

A Python 3.7 wrapper around multiprocessing for easy cross-machine
computation

What is this?
-------------

Distributed Worker is a wrapper around the multiprocessing package
allowing you to focus on the distributed computations instead of
managing nodes/communication.
You can use regular python primitives to communicate just as in
multiprocessing, but you can also use remote machines as workers.

How does it work?
-----------------

You create a ``DistributedManager`` which creates a central server for
your workers to connect to.
You can create some logic around it to manage tasks/messages.

Then you implement one or multiple ``DistributedWorker``\ s to handle
those tasks.

And now you can run your distributed computations.

Example Setup
-------------

    Check ``/example.py`` for a fully functional version

Let's say we want a distributed prime checker, here is a very naive
implementation:
``py def is_prime(x):   for num in range(2, x):     if (x % num) == 0:       return False   return True``

If we want to check a large amount of primes that would take ages, so we
want to distribute the task.

    To be clear this task is likely overkill for a distributed setup,
    but it's a good example

First we will create a task server:

\`\`\`py
from distributed\_worker import DistributedManager
class PrimeManager(DistributedManager):
def **init**\ (self):
::

    super().__init__()
    self.pending = list(range(150000))
    self.results = {}
    self.tasked = set()
    self.chunks = 1000 # Task size

def loop(self):
::

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

def on\_new\_worker(self, worker: int):
::

    print('New worker added %d' % worker)

def on\_worker\_disconnect(self, worker: int):
::

    print('Worker disconnected %d' % worker)

def handle\_msg(self, worker: int, msg: Any):
::

    # Worker finished it's task
    for num in msg:
      self.results[num] = msg[num]
    self.tasked.remove(worker)

if **name** == "**main**\ ":
::

    manager = PrimeManager()

    # For adding remote workers
    print('client creds:', manager.get_client_args())

    while manager.tasked or manager.pending:
      manager.run_once()
      # Can do other tasks here as well

    # Print the results
    print(manager.results)

    # Stop all workers
    manager.stop()

\`\`\`

Then we'll create a worker:

\`\`\`py
from distributed\_worker import DistributedWorker
class PrimeWorker(DistributedWorker):
def **init**\ (self, pipe, \*args, \*\*kwargs):
::

    super().__init__(pipe)
    self.task = []
    self.results = {}

def loop(self):
::

    # Ideally keep the executing here within 1 hour or adjust TTL on the server
    if len(self.task):
      # Tasks available
      ctask = self.task.pop()
      self.results[ctask] = is_prime(ctask)
    else:
      # Finished tasks
      if len(self.results):
        self.send(self.results)
        # Clear results so we don't resend
        self.results = {}

def handle\_msg(self, msg):
::

    if type(msg) == list:
      self.task = msg

\`\`\`

Now we can create distributed workers gallore:
\`\`\`py
from distributed\_worker import create\_remote\_worker

import PrimeWorker as well
==========================

Example, check console of server
================================

client\_args = (('localhost', 6000), 'AF\_INET', b'secret password')

Create 10 workers (10 threads)
==============================

for x in range(10):
# Add PrimeWorker constructor args if needed
create\_remote\_worker(PrimeWorker, client\_args)
\`\`\`

If we just want to utilize our local CPU cores (and not deal with the
authentication) we can create workers through the manager:
``py manager = DistributedManager() # Again, add PrimeWorker constructor args if needed manager.create_local_worker(PrimeWorker)``

    The total execution time will generally improve as tasks need more
    time to complete

Running ``example.py`` vs a single-threaded version:
\`\`\`
$ time example.py
...
real 0m11.631s
user 0m57.648s
sys 0m0.395s

$ time single.py
real 0m43.581s
user 0m43.550s
sys 0m0.018s
\`\`\`
