import Std

namespace Eval18


theorem nat_mul_zero_eval (n : Nat) : n * 0 = 0 :=
  -- PROOF_START
  by exact Nat.mul_zero n
  -- PROOF_END

end Eval18
