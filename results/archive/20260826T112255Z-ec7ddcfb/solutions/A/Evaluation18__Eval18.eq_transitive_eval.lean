import Std

namespace Eval18


theorem eq_transitive_eval {α : Type} {a b c : α} : a = b → b = c → a = c :=
  -- PROOF_START
  fun h1 h2 => h1.trans h2
  -- PROOF_END

end Eval18
