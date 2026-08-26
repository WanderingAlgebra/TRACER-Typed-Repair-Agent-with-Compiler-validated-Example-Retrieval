import Std

namespace Eval18


theorem or_swap_eval (p q : Prop) : p ∨ q → q ∨ p :=
  -- PROOF_START
  fun h : p ∨ q => h.elim Or.inr Or.inl
  -- PROOF_END

end Eval18
