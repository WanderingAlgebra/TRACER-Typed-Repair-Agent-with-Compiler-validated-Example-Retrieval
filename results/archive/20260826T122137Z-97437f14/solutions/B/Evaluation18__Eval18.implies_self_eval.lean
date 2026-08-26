import Std

namespace Eval18


theorem implies_self_eval (p : Prop) : p → p :=
  -- PROOF_START
  fun h : p => h
  -- PROOF_END

end Eval18
