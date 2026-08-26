# AI 辅助预审（不等同于人工复核）

实验 ID：`pilot-20260826T011418Z-06ffd827`

本文件记录对 54 个 A/B/C 成功证明的 AI 辅助预审。它不能替代研究协议要求的真人复核，且未修改 `manual_review.csv`。

## 自动与语义检查结果

- 54/54 个 `results/solutions/<condition>/*.lean` 文件使用仓库 Lean 工具链重新编译通过。
- 54/54 个保存文件的目标声明指纹与冻结 benchmark 匹配，未发现修改定理陈述。
- 54/54 个证明都只包含一个 `PROOF_START`/`PROOF_END` 区域。
- 未发现 `sorry`、`sorryAx`、`admit`、新增 `axiom`、`unsafe`、`run_tac`、`run_term_elab`、`#eval`、`elab_rules` 或 `macro_rules`。
- Provider 错误 0，基础设施错误 0，缓存命中 0。
- 条件 C 的检索语料与冻结题目之间没有完全相同或仅 binder 改名的声明。
- 逐项阅读最终候选后，未发现证明引入题目之外的假设；所有候选都使用局部假设、Lean 标准构造子、标准定理或普通 tactic 完成目标。

## 逐题预审

表中 `通过` 只表示 AI 预审通过，不是人工签字。

| problem_id | A | B | C | 最终证明语义 | C 检索相似度说明 |
|---|---|---|---|---|---|
| `and_swap_eval` | 通过 | 通过 | 通过 | 从输入合取分别取出左右分量并反向构造合取 | 高：检索示例包含嵌套合取重排，但不是同一或等价定理 |
| `or_swap_eval` | 通过 | 通过 | 通过 | 对析取分类并交换 `Or.inl`/`Or.inr` | 中：检索示例展示析取消去，但不包含交换结论 |
| `eq_transitive_eval` | 通过 | 通过 | 通过 | 使用 `Eq.trans`/`.trans` 连接两段等式 | 中：检索包含等式对称和函数等式应用，不含传递性目标 |
| `function_congruent_eval` | 通过 | 通过 | 通过 | 使用 `congrArg` 或对输入等式分类后 `rfl` | 高：检索包含函数等式在参数上的应用，结构相关但方向和目标不同 |
| `nat_add_zero_eval` | 通过 | 通过 | 通过 | 使用标准定理 `Nat.add_zero` | 中：检索包含 `Nat.add_succ`，不含右加零答案 |
| `nat_zero_add_eval` | 第 2 轮通过 | 第 2 轮通过 | 通过 | 使用标准定理 `Nat.zero_add` | 中：检索包含 `Nat.add_succ`，不含左加零答案 |
| `nat_succ_ne_zero_eval` | 通过 | 通过 | 通过 | 对等式分类得矛盾，或使用 `Nat.succ_ne_zero` | 中：检索包含后继单射，不含后继非零结论 |
| `nat_le_transitive_eval` | 通过 | 通过 | 通过 | 使用 `Nat.le_trans` 连接两段小于等于关系 | 低：检索只包含自反关系和其他自然数引理 |
| `bool_cases_eval` | 通过 | 通过 | 通过 | 对 Bool 分类并由 `simp` 关闭两个分支 | 低：检索示例与 Bool 分类无直接对应 |
| `identity_application_eval` | 通过 | 通过 | 通过 | 由定义化简使用 `rfl` | 低：检索示例与恒等函数化简不同 |
| `and_assoc_eval` | 通过 | 通过 | 通过 | 拆解嵌套合取并按目标结构重新组合 | 中：检索包含其他嵌套合取投影，不含结合律目标 |
| `or_assoc_eval` | 通过 | 通过 | 通过 | 两层析取分类并按目标嵌套结构重建 | 中：检索展示析取消去模式，但不含结合律目标 |
| `not_not_intro_eval` | 通过 | 通过 | 通过 | 引入 `p` 与 `¬p` 后应用否定得到矛盾 | 高：检索包含 `p ∧ ¬p → False`，直接相关但不是同一声明或完整目标答案 |
| `nat_succ_add_eval` | 通过 | 通过 | 通过 | 使用标准定理 `Nat.succ_add` | 高：检索包含名称和结构相近的 `Nat.add_succ`，但左右递归方向不同 |
| `nat_add_comm_eval` | 通过 | 通过 | 通过 | 使用标准定理 `Nat.add_comm` | 中：检索包含自然数加法后继引理，不含交换律答案 |
| `nat_mul_zero_eval` | 通过 | 通过 | 通过 | 使用 `simp` 或标准定理 `Nat.mul_zero` | 中：检索为其他自然数引理，不含乘零答案 |
| `nat_lt_succ_self_eval` | 通过 | 通过 | 通过 | 使用标准定理 `Nat.lt_succ_self` | 低：检索只包含自然数关系相关示例，不含该结论 |
| `implies_self_eval` | 通过 | 通过 | 通过 | 引入命题证明后原样返回 | 低：检索示例不包含蕴含自反目标 |

## 需要真人决定的边界

按“直接答案泄漏”的标准，条件 C 未发现泄漏。但 `and_swap_eval`、`function_congruent_eval`、`not_not_intro_eval` 和 `nat_succ_add_eval` 的检索示例与目标具有较高结构相似度。相关示例本来就是条件 C 的实验变量，因此“相似”不自动等于“泄漏”；真人复核者仍需确认研究中采用的是“禁止同题/等价答案”还是更严格的“禁止高度类似示例”口径。

如果真人接受当前项目文档采用的“禁止同题或等价答案”口径，则本次 AI 预审建议 54 项均为：`kernel_pass=yes`、`inappropriate_assumption=no`、`leakage_risk=no`。最终是否写入 `manual_review.csv` 必须由真人确认。
