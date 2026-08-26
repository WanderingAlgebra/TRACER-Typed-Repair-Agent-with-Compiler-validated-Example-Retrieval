-- tags: equality functions
example {α : Type} {a b : α} : a = b → b = a := by
  intro hab
  exact hab.symm

example {α β : Type} {f g : α → β} (a : α) : f = g → f a = g a := by
  intro hfg
  cases hfg
  rfl
