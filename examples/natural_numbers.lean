-- tags: natural_numbers rewriting relations
example (n : Nat) : n + 0 = n := by exact Nat.add_zero n
example (n m : Nat) : Nat.succ n + m = Nat.succ (n + m) := by exact Nat.succ_add n m
example (n : Nat) : n < Nat.succ n := by exact Nat.lt_succ_self n
