import Std

namespace Eval18


theorem not_not_intro_eval (p : Prop) : p → ¬¬p :=
  -- PROOF_START
  fun h hn => hn h
  -- PROOF_END

end Eval18
