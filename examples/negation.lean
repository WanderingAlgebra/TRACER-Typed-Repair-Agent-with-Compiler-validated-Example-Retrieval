-- tags: propositional_logic negation
example (p : Prop) : p → p := by
  intro hp
  exact hp
