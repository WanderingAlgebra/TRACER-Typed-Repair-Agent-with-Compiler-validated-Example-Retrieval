import Std

namespace Eval18


theorem or_assoc_eval (p q r : Prop) : p ∨ (q ∨ r) → (p ∨ q) ∨ r :=
  -- PROOF_START
  fun h =>
  match h with
  | Or.inl hp => Or.inl (Or.inl hp)
  | Or.inr hqr =>
    match hqr with
    | Or.inl hq => Or.inl (Or.inr hq)
    | Or.inr hr => Or.inr hr
  -- PROOF_END

end Eval18
