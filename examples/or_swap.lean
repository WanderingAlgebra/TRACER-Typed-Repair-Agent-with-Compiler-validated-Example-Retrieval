-- tags: propositional_logic or
example (p q r : Prop) : (p → r) → (q → r) → p ∨ q → r := by
  intro hpr hqr h
  cases h with
  | inl hp => exact hpr hp
  | inr hq => exact hqr hq
