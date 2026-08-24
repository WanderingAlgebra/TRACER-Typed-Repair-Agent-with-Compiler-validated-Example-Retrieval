-- tags: equality functions
example {α : Type} {a b c : α} : a = b → b = c → a = c := by
  intro hab hbc
  exact Eq.trans hab hbc

example {α β : Type} (f : α → β) {a b : α} : a = b → f a = f b := by
  intro hab
  cases hab
  rfl
