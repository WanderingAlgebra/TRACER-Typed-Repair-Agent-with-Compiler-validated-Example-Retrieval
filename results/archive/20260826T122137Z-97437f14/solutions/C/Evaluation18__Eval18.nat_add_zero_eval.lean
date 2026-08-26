import Std

namespace Eval18


theorem nat_add_zero_eval (n : Nat) : n + 0 = n :=
  -- PROOF_START
  Nat.add_zero n
  -- PROOF_END

end Eval18
