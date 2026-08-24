-- tags: propositional_logic negation
example (p : Prop) : p → ¬¬p := by
  intro hp hnp
  exact hnp hp
