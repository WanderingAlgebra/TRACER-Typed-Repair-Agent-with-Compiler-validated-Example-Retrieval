import Std

namespace Eval18


theorem and_swap_eval (p q : Prop) : p ∧ q → q ∧ p :=
  -- PROOF_START
  fun ⟨hp, hq⟩ => ⟨hq, hp⟩
  -- PROOF_END

end Eval18
