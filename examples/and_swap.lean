-- tags: propositional_logic and
example (p q : Prop) : p ∧ q → q ∧ p := by
  intro h
  exact And.intro h.right h.left
