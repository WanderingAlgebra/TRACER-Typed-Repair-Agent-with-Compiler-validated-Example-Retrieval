import Std

namespace Eval18


theorem and_swap_eval (p q : Prop) : p ∧ q → q ∧ p :=
  -- PROOF_START
  fun h : p ∧ q => ⟨h.2, h.1⟩
  -- PROOF_END

end Eval18
