def is_prime(x):
  for num in range(2, x):
    if (x % num) == 0:
      return False
  return True

if __name__ == "__main__":
  resulting = {}
  pending = list(range(150000))
  while len(pending):
    task = pending.pop()
    resulting[task] = is_prime(task)
