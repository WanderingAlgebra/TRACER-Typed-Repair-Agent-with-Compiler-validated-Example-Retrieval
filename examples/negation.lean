-- tags: propositional_logic negation
example (p : Prop) : p ∧ ¬p → False := by
  intro h
  exact h.right h.left
