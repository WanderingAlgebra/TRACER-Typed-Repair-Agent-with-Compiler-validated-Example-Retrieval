-- tags: natural_numbers rewriting relations
example (n m : Nat) : n + Nat.succ m = Nat.succ (n + m) := by exact Nat.add_succ n m
example {n m : Nat} : Nat.succ n = Nat.succ m → n = m := by
  intro h
  exact Nat.succ.inj h
example (n : Nat) : n ≤ n := by exact Nat.le_refl n
