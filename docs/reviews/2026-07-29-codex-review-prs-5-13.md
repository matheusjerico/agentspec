# Revisão Codex — Incrementos 5–13 (PRs #5–#13)

> Revisão adversarial cross-model (Codex) sobre o diff acumulado dos nove
> incrementos do programa de melhorias. Veredito: **needs-attention** — três
> caminhos fail-open confirmados no spec-linter. Nenhuma correção foi aplicada;
> este documento mapeia exatamente o que precisa mudar.

| Atributo | Valor |
|----------|-------|
| **Data** | 2026-07-29 |
| **Escopo** | PRs #5–#13 (main `03f9119` → `6164c32`), 98 arquivos, ~20.3k linhas |
| **Revisor** | Codex (adversarial-review via companion) |
| **Veredito** | needs-attention (2 high, 1 medium) |
| **Status** | Achados mapeados — correções pendentes de execução |

---

## Finding 1 — [HIGH] Configuração malformada desativa gates silenciosamente

**Onde:** `tools/spec-linter/spec_linter/cli.py:231-295` (função `_build_report_contract`)

**Defeito:** os quatro blocos opt-in (`tdd_policy`, `task_review`, `traceability`,
`workflow_metrics`) armam suas regras apenas quando `isinstance(data.get(X), dict)`.
Um bloco **presente porém inválido** (null, string, lista, mapping incompleto —
p.ex. por um erro de indentação no YAML) não gera erro: o CLI passa `None`/`False`
e as regras correspondentes simplesmente não rodam. Um typo desliga o TDD
obrigatório, a revisão por tarefa, a cobertura MUST ou as métricas — sem nenhum
sinal.

**Alterações necessárias:**

1. Em `cli.py`, para cada um dos quatro blocos, separar os três casos:
   - chave **ausente** → fallback atual (regras dormentes, compatibilidade preservada);
   - chave presente e **mapping válido** → armar as regras (comportamento atual);
   - chave presente com **valor não-mapping** (null/string/lista/int) → `raise _OperationalError`
     nomeando o bloco e o tipo encontrado (exit 2, fail-closed).
2. `traceability`: hoje qualquer dict arma `matrix_must_coverage=True` sem validar
   subestrutura. Validar a estrutura mínima esperada antes de armar (e falhar
   fechado se o dict existir mas a estrutura mínima estiver ausente/errada).
3. Espelhar a mesma disciplina em `_design_phase_contract` (ou equivalente) para
   os blocos que o lado design consome (`task_manifest`, `traceability`).
4. **Testes:** parametrizados em `tools/spec-linter/tests/test_cli.py` — para cada
   um dos quatro blocos: `null`, lista, string e mapping incompleto → exit 2 com
   mensagem nomeando o bloco; ausência → regras dormentes (verde).
5. Replicar em `plugin/tools/spec-linter/` via `./build-plugin.sh` (nunca editar a
   cópia à mão) e confirmar `tests/test_plugin_parity.py` verde.

---

## Finding 2 — [HIGH] Linha MUST truncada some da matriz e passa sem cobertura

**Onde:** `tools/spec-linter/spec_linter/contracts/build_report.py:165-183`
(`_parse_matrix_rows`) — e o parser equivalente em
`tools/spec-linter/spec_linter/contracts/design_phase.py`

**Defeito:** linhas numeradas da Traceability Matrix com menos de 8 células, ou com
placeholder `{` em REQ/Priority, são descartadas **sem finding** (residual
divulgado em comentário, mas explorável). Como a seção existe, `matrix_present`
fica `True` e `BR.matrix_missing` não dispara; a linha descartada nunca chega a
`BR.must_uncovered`. Um report de risco alto pode truncar exatamente a linha MUST
sem testes e obter PASS.

**Alterações necessárias:**

1. Em `_parse_matrix_rows` (build side): toda linha numerada com cardinalidade
   incorreta (< 8 células) ou placeholder em REQ/Priority vira **finding FAIL**
   (nova regra, p.ex. `BR.matrix_row_malformed`), em qualquer nível de risco —
   nunca descarte silencioso.
2. Aplicar o mesmo fail-closed no parser da matriz em `design_phase.py`
   (linhas < 5–6 células conforme o shape do design) — p.ex. `TX.matrix_row_malformed`.
3. Remover/atualizar os comentários "disclosed residual" correspondentes — o
   residual deixa de existir.
4. **Testes:** linhas MUST truncadas de 1–7 células (build) e 1–5 células (design),
   linha com placeholder em REQ, linha com placeholder em Priority → FAIL nomeando
   a linha; matriz íntegra continua PASS. Atualizar fixtures existentes que
   dependam do descarte silencioso, se houver.
5. Rebuild do plugin + parity.

---

## Finding 3 — [MEDIUM] Task Review malformado escapa de todas as regras em risco baixo

**Onde:** `tools/spec-linter/spec_linter/contracts/build_report.py:275-289`
(parse das linhas de `## Task Reviews`)

**Defeito:** linhas com menos de 5 células ou com placeholder são ignoradas sem
diagnóstico. Em risco **low**, `BR.task_review_missing` é silencioso por política;
como a linha ignorada não entra em `task_review_rows`, `BR.task_review_dirty`
nunca avalia seu verdict. Um verdict `dirty` pode ser escondido por truncamento
da própria linha.

**Alterações necessárias:**

1. Emitir **FAIL** (p.ex. `BR.task_review_row_malformed`) para qualquer linha
   numerada da seção Task Reviews com < 5 células ou placeholder em task-id/verdict,
   independentemente do nível de risco (o gate de severidade de
   `task_review_missing` não se aplica a malformação).
2. Remover/atualizar o comentário de residual divulgado correspondente.
3. **Testes de regressão:** linha curta contendo `dirty` no texto; placeholder no
   verdict; linha sem a coluna de verdict — todos em risco `low` → FAIL. Linhas
   válidas seguem o comportamento atual.
4. Rebuild do plugin + parity.

---

## Plano de execução sugerido (ordem)

| # | Passo | Verificação |
|---|-------|-------------|
| 1 | Finding 2 e 3 (mesmo arquivo, mesmo padrão fail-closed de parser) — TDD RED-first | novos testes falham antes, passam depois |
| 2 | Finding 1 (cli.py, quatro blocos + validação mínima de traceability) | testes parametrizados exit 2 |
| 3 | Espelho no design_phase.py (Finding 2) | suite design verde |
| 4 | `./build-plugin.sh` (nunca editar plugin/ à mão) | exit 0 + test_plugin_parity verde |
| 5 | Suites completas | root + spec-linter verdes (hoje: 172 + 193) |
| 6 | Bump WORKFLOW_CONTRACTS (v3.16.1 ou v3.17.0) + entrada no version_history descrevendo o endurecimento fail-closed | teste documental do history |
| 7 | PR único de hardening consumindo o fluxo normal (/auto ou /build direto) | merge verificado |

## Observações do revisor sobre o ambiente

- O Codex não executou a suíte (pytest fora do PATH no ambiente dele e cache uv
  bloqueado por workspace read-only) — os achados foram confirmados por leitura
  de código, com os comentários de "disclosed residual" do próprio código como
  evidência. Rodar as suítes localmente (`rtk proxy python3 -m pytest`) durante
  a correção.
- Os três achados compartilham uma mesma classe: **descarte silencioso /
  fallback silencioso em vez de fail-closed** — a mesma lição que o programa já
  aplicou em outros pontos (vocabulário fechado, guards de placeholder), agora
  pendente nos parsers de linha e no wiring de configuração.
