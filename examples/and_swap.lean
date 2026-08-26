-- tags: propositional_logic and
example (p q : Prop) : p ∧ q → p := by
  intro h
  exact h.left

example (p q r : Prop) : p ∧ (q ∧ r) → r ∧ p := by
  intro h
  exact And.intro h.right.right h.left
