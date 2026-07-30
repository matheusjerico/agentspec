# Residuais do PR A (EXACT_SECTIONS) → entrada obrigatória do PR B

> Handoff de escopo. O PR A fechou o endereçamento de seções (spec §6). Cinco
> bypasses **permanecem abertos** e são de gramática de tabela — escopo do §7 /
> PR B, cujo entregável é o parser estrutural de tabelas. Este documento existe
> para que o DEFINE do PR B os consuma com repro pronto, em vez de redescobri-los.

| Atributo | Valor |
|---|---|
| **Origem** | 4 rounds de revisão adversarial no run EXACT_SECTIONS (2026-07-30) |
| **Veredito final do PR A** | clean-with-minors — nenhum bypass de endereçamento restante |
| **Decisão de escopo** | Ratificada pelo mantenedor: PR A entrega §6; residuais vão ao PR B |
| **Estado do PR A** | 18/18 vetores de endereçamento bloqueados; corpus arquivado 15/15 limpo |
| **Severidade dos residuais** | Critical (permitem PASS com finding bloqueante aberto) |

---

## R-1 — Tabela severada com header próprio e coluna de resolução renomeada

**Mecanismo:** `_findings_tables` identifica a tabela de findings pela assinatura
do header (`Severity` **e** `Resolution`). Uma tabela separada da seção por um
heading de fronteira, mas que declara header próprio com `Status` no lugar de
`Resolution`, não casa a assinatura — e, por ter header, também não herda o
header anterior.

```markdown
## Review Verdict
| 1 | Minor | cosmético | foo.py:1 | fixed in abc123 |

## Files Created
- src/x.py

| # | Severity | Description | Location | Status |
|---|----------|-------------|----------|--------|
| 1 | Critical | SQL injection | db.py:42 |  |
```
→ **PASS** (nenhum finding).

**Direção da correção no PR B:** vocabulário fechado para nomes de coluna de
resolução (`resolution`, `status`, `fix`, `resolved in`…) **ou**, melhor, um
parser de tabela que reconheça a tabela por posição/estrutura e trate header
não reconhecido como `MalformedRow`/FAIL em vez de "não é tabela de findings".

## R-2 — Linha sem a célula `#` inicial

**Mecanismo:** `_NUMBERED_ROW` exige `^\|\s*\d+\s*\|`. Remover a primeira
célula torna a linha invisível a todos os scans (na seção e no safety net).

```markdown
| Critical | SQL injection | db.py:42 |  |
```
→ **PASS**. Pré-existente (Incremento 1), não tocado pelo PR A.

**Direção no PR B:** o parser estrutural deve classificar toda linha de tabela
por cardinalidade e conteúdo, não exigir numeração; linha de tabela em região
de findings sem numeração = `MalformedRow` → FAIL (§7.3 já prevê o modelo).

## R-3 — Tabela HTML crua

**Mecanismo:** `_TABLE_ROW`/`_table_blocks` exigem sintaxe de pipe. Um
`<table><tr><td>Critical…` renderiza normalmente no GitHub e é invisível a
qualquer regra deste contrato.

→ **PASS**. Pré-existente e universal (afeta matriz, task reviews e métricas
também, não só o Review Verdict).

**Direção no PR B:** decidir política explícita — (a) proibir HTML cru em
artefatos de contrato (FAIL ao detectar `<table`), ou (b) parsear. (a) é
fail-closed, barato e alinhado ao princípio §4.1.

## R-4 — Palavra de severidade não reconhecida

**Mecanismo:** o PR A passou a ler a célula por *palavras* (então
`Critical (F1)`, `**Critical**`, `🔴 Critical`, `critical/high` bloqueiam), mas
o vocabulário segue fechado em `{critical, important}`. Uma palavra fora dele
—`Blocker`, `Sev-1`, um typo, um homóglifo cirílico (`Сritical`)— não bloqueia.

→ **PASS**. Pré-existente.

**Direção no PR B:** severidade **desconhecida** em tabela de findings bloqueia
(mesmo padrão de vocabulário fechado já usado para config e chaves de métricas),
com normalização unicode (NFKC + detecção de homóglifos) antes do match. Cuidado
de falso-positivo: aplicar só a linhas de uma tabela de findings identificada,
nunca a qualquer linha numerada da seção.

## R-5 — Linha severada com largura de coluna diferente

**Mecanismo:** a herança de header por fragmento é escopada por **largura**
(continuação de tabela preserva a contagem de colunas). Isso é o que impede o
falso-positivo de uma tabela sem header numa seção posterior herdar identidade
de "findings". O preço: uma linha severada e *preenchida com colunas extras*
não casa a largura e escapa.

```markdown
## Review Verdict
| # | Severity | Description | Location | Resolution |
|---|----------|-------------|----------|------------|
| 1 | Minor | cosmético | foo.py:1 | fixed in abc123 |

## Files Created
- src/x.py

| 2 | Critical | SQL injection | db.py:42 |  | padding |
```
→ **PASS**.

**Direção no PR B:** o parser estrutural resolve isso na raiz — linha de tabela
em região de findings com largura inconsistente é `MalformedRow` → FAIL (§7.3),
em vez de "não é uma continuação".

---

## Por que não foram corrigidos no PR A

O escopo do PR A (§6) é **endereçamento**: onde uma seção começa e termina. Os
cinco residuais são de **gramática de tabela**: o que é uma linha e o que suas
células significam. Corrigi-los com heurísticas de forma dentro do PR A já
produziu, comprovadamente, dois falsos-positivos em reports legítimos (tabela
partida por linha em branco; tabela de exemplo dentro de fence) — e um gate que
grita em artefato válido é contornado, o que é falha de segurança própria. O §16
sequencia A → B exatamente por isso.

## Estado após o PR B (2026-07-30)

R-1 a R-5 **fechados** e verificados nas duas variantes (duplicada e movida).
Um residual novo, estreito e documentado, nasce da correção do R-1 e vai para
o **PR F** (§11, consolidação de parser/modelos):

**R-6 — tabela de findings com nomes de coluna totalmente fora do vocabulário.**
O reconhecimento de tabela *com header* é por vocabulário fechado de colunas
(`severity|sev|level|impact|criticality` × `resolution|status|outcome|fix|
disposition|state|result`). Um header inteiramente estrangeiro não é
reconhecido. Tentou-se reconhecimento por conteúdo e foi removido: por
conteúdo, uma célula que *é* a palavra "Important" numa tabela de decisões é
indistinguível de uma linha de finding — três construções legítimas do próprio
template ficaram vermelhas. Remédio sancionado: estender o vocabulário (uma
linha de dado de contrato). Valores desconhecidos seguem fail-closed.

## Lição transversal (vale para o PR B e para o resto do programa)

Os quatro rounds convergiram num invariante único, que o revisor formulou melhor
que eu:

> **o conjunto de construções confiadas para delimitar evidência sempre foi
> maior que o conjunto vigiado contra abuso dessa confiança.**

Cada round fechou a instância reportada e o seguinte achou outra uma camada
abaixo: prefixo de heading → nível de heading → região opaca → heading de
fronteira não vigiado → gramática de célula. O PR B fecha a camada de tabela; ao
projetá-lo, a pergunta a fazer não é "esta construção específica escapa?" mas
"qual é o conjunto que confio, e ele é *igual* ao que vigio?".
