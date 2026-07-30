# Especificação de remediação arquitetural do AgentSpec

> Correções e melhorias necessárias após a revisão dos incrementos de rigor adaptativo

## 1. Metadados

| Campo | Valor |
|---|---|
| Status | Pronto para revisão |
| Data | 2026-07-29 |
| Baseline | `03f9119..6164c32` |
| Branch revisada | `main` |
| Escopo revisado | PRs 5 a 13 e estado consolidado do AgentSpec |
| Natureza | Correção, hardening, enforcement e validação de release |
| Implementação | Não iniciada por este documento |

## 2. Objetivo

Este documento especifica todas as melhorias que devem ser executadas após a
revisão arquitetural da implementação incremental do AgentSpec. Ele transforma
os achados da revisão em um programa de remediação verificável, ordenado por
risco e dependências.

O objetivo é garantir que as capacidades introduzidas — perfil de risco,
manifesto de tarefas, TDD orientado por risco, Task Review, rastreabilidade,
controle de commits e paralelismo, PR Readiness e métricas — deixem de depender
de convenções frágeis e passem a fornecer enforcement confiável.

O programa estará concluído somente quando:

- nenhum finding bloqueante puder ser ocultado por variações de Markdown;
- requisito MUST malformado ou sem cobertura falhar de forma fechada;
- PR Readiness possuir validação executável;
- o build do plugin executar todas as suítes dos componentes distribuídos;
- novos artefatos adotarem obrigatoriamente os contratos atuais;
- compatibilidade legada continuar explícita e auditável;
- o benchmark de regressão demonstrar correção, rigor e eficiência.

## 3. Resumo executivo da revisão

A arquitetura geral evoluiu de forma coerente. `.claude/` permaneceu como fonte
canônica, `plugin/` é gerado, os contratos são versionados e o Spec Linter ganhou
validadores especializados para Define, Design e Build Report.

Entretanto, a revisão encontrou quatro lacunas bloqueantes e uma lacuna de
maturidade:

1. um heading cujo nome começa com `Review Verdict` pode ocultar findings
   Critical ou Important abertos;
2. linhas truncadas nas matrizes são descartadas silenciosamente e podem receber
   PASS;
3. PR Readiness ainda é majoritariamente um contrato documental;
4. o build do plugin não executa as suítes do Spec Linter e Spec Judge;
5. capacidades centrais continuam em `Observe`, `Warn` ou opt-in, embora a
   definição final do programa exija enforcement.

Esses problemas impedem tratar o estado atual como uma release final do novo
workflow.

## 4. Princípios da remediação

### 4.1 Fail-closed para evidência obrigatória

Artefato malformado nunca equivale a artefato ausente ou válido. Se uma seção
obrigatória existe, mas não pode ser interpretada integralmente, o resultado é
FAIL.

### 4.2 Endereço exato para seções contratuais

Seções fixadas por template devem ser localizadas por slug exato. Prefix matching
é permitido somente para conteúdo não contratual e quando a ambiguidade for
intencional.

### 4.3 Parser único por formato

Heading, tabela Markdown, metadata table e YAML fence devem ser interpretados por
componentes compartilhados. Contratos de fase não devem manter implementações
ligeiramente diferentes do mesmo parser.

### 4.4 Política declarativa precisa ter consumidor executável

Uma entrada em `WORKFLOW_CONTRACTS.yaml` deve declarar se é:

- `documentation_only`;
- `observe`;
- `warn`;
- `enforce`.

Blocos marcados como `enforce` precisam indicar o componente executável e os
testes comportamentais correspondentes.

### 4.5 Testes adversariais fazem parte do contrato

Cada correção de parser deve incluir casos decoy, truncados, duplicados,
reordenados, incompletos e com placeholders. Happy paths não são evidência
suficiente para gates.

### 4.6 Compatibilidade não significa silêncio

Artefatos legados podem receber adaptação ou WARN, mas ausência de evidência
nunca deve ser convertida em PASS implícito.

## 5. Arquitetura-alvo

Separar o mecanismo em quatro camadas:

```text
Markdown/YAML
    ↓
Parser estrutural compartilhado
    ↓
Modelos tipados de artefato
    ↓
Contratos de fase e gates
    ↓
CLI / Build / Ship / Create PR
```

### 5.1 Parser estrutural

Responsável exclusivamente por:

- headings e limites de seção;
- tabelas e quantidade de colunas;
- metadata tables;
- YAML fences;
- localização precisa de erros.

O parser não decide severidade nem política.

### 5.2 Modelos tipados

Representam:

- `DefineArtifact`;
- `DesignArtifact`;
- `BuildReportArtifact`;
- `PrReadyArtifact`;
- `TraceabilityRow`;
- `ReviewFinding`;
- `TaskReview`;
- `WorkflowMetrics`.

Um modelo nunca descarta uma linha inválida. Ele retorna valor ou erro
estruturado.

### 5.3 Contratos

Recebem modelos válidos ou erros de parsing e aplicam:

- vocabulários;
- obrigatoriedade;
- severidade;
- compatibilidade;
- regras entre campos;
- regras entre artefatos.

### 5.4 Consumidores

Build, Ship e `/create-pr` devem consumir verdicts gerados pelos contratos, sem
reimplementar a mesma regra em prosa.

## 6. Remediação 1 — Fechar o bypass de Review Verdict

### 6.1 Severidade

**Critical.**

### 6.2 Evidência

`BuildReportContract.parse()` usa:

```python
_section_after(artifact, "review_verdict")
```

`_section_after` aceita qualquer slug que comece com o prefixo. Portanto,
`## Review Verdict Notes` pode ser selecionada antes de `## Review Verdict`.

Reprodução confirmada:

1. usar um Build Report válido;
2. adicionar `## Review Verdict Notes` antes da seção real;
3. mudar a resolução de um finding Critical para `OPEN`;
4. executar `spec-lint --phase build --legacy-mode fail`;
5. resultado observado: PASS.

### 6.3 Causa-raiz

O contrato possui `_section_exact`, mas apenas algumas seções foram migradas
para ele. A API antiga por prefixo permaneceu em superfícies críticas.

### 6.4 Implementação

1. Substituir prefix matching por exact matching em:
   - `Review Verdict`;
   - `Task Execution with Agent Attribution`;
   - `TDD Evidence`;
   - qualquer outra seção de template com nome fixo.
2. Remover `_section_after` do caminho dos gates.
3. Fazer heading duplicado produzir FAIL.
4. Fazer heading com nível incorreto produzir `required_section` FAIL.
5. Preservar o texto da seção selecionada e sua posição para mensagens de erro.
6. Adicionar regra genérica `MD.duplicate_contract_section`.

### 6.5 Arquivos principais

- `tools/spec-linter/spec_linter/contracts/build_report.py`
- novo módulo compartilhado de parsing
- `tools/spec-linter/tests/test_build_report_contract.py`
- `tools/spec-linter/tests/test_cli.py`
- cópia empacotada gerada em `plugin/tools/spec-linter/`

### 6.6 Testes obrigatórios

- decoy antes da seção real;
- decoy depois da seção real;
- duas seções exatas;
- `### Review Verdict` em vez de `##`;
- Critical aberto na seção real;
- Important aberto na seção real;
- finding resolvido com `fixed in <sha>`;
- resolução semelhante, mas inválida;
- relatório canônico continuando com PASS.

### 6.7 Critérios de aceite

- nenhuma variação de prefixo altera o escopo da revisão;
- finding Critical/Important aberto sempre gera FAIL;
- seção duplicada sempre gera FAIL;
- a reprodução original passa a falhar;
- todos os Build Reports arquivados continuam validáveis ou recebem diagnóstico
  explícito de migração.

## 7. Remediação 2 — Tornar tabelas fail-closed

### 7.1 Severidade

**High.**

### 7.2 Evidência

Os parsers de Design e Build descartam linhas numeradas com menos colunas do que
o template. Uma linha como:

```markdown
| 1 | REQ-001 | MUST |
```

desaparece da coleção validada. A reprodução no Build Report retornou PASS.

### 7.3 Causa-raiz

O parser retorna somente linhas válidas. Não existe uma representação de
`MalformedRow`; consequentemente, o contrato não sabe que uma linha foi
encontrada e descartada.

### 7.4 Implementação

Criar um parser de tabela que retorne:

```python
ParsedTable(
    headers=[...],
    rows=[ParsedRow(...)],
    errors=[TableError(...)],
)
```

Cada erro deve conter:

- seção;
- número da linha;
- quantidade esperada e encontrada de células;
- conteúdo original;
- tipo de erro.

Tipos mínimos:

- `column_count`;
- `missing_header`;
- `duplicate_header`;
- `empty_required_cell`;
- `placeholder`;
- `invalid_identifier`;
- `duplicate_identifier`;
- `unexpected_extra_column`.

### 7.5 Superfícies afetadas

- Traceability Matrix do Design;
- Traceability Matrix do Build Report;
- Task Reviews;
- Task Execution;
- Review Findings;
- tabelas de metadata usadas como contrato.

### 7.6 Regras adicionais

1. Quando a matriz está presente, deve conter ao menos uma linha válida ou uma
   declaração estruturada de que não há requisitos.
2. `REQ-ID` deve ser único.
3. Cada requisito MUST do Define deve aparecer exatamente uma vez na matriz.
4. Cada task ID referenciado deve existir no manifesto v2.
5. Cada MUST deve possuir task, teste, tipo de verificação e resultado.
6. Exceções devem usar categoria fechada e justificativa.
7. Placeholder nunca é ignorado; produz FAIL em artefato com status final.

### 7.7 Arquivos principais

- novo `tools/spec-linter/spec_linter/markdown/`
- `contracts/design_phase.py`
- `contracts/build_report.py`
- novo validador cross-artifact
- testes de Design e Build Report

### 7.8 Testes obrigatórios

- linha curta;
- linha longa;
- coluna ausente no meio;
- pipe escapado;
- placeholder;
- REQ duplicado;
- REQ sem task;
- task desconhecida;
- MUST sem teste;
- MUST com resultado diferente de pass;
- exceção válida;
- exceção inválida;
- matriz vazia;
- header malformado.

### 7.9 Critérios de aceite

- nenhuma linha reconhecida é descartada silenciosamente;
- qualquer erro estrutural em evidência obrigatória gera FAIL;
- a reprodução original passa a falhar;
- mensagens apontam seção e linha;
- o parser é compartilhado entre Design e Build.

## 8. Remediação 3 — Criar PR Readiness executável

### 8.1 Severidade

**High.**

### 8.2 Estado atual

`WORKFLOW_CONTRACTS.yaml` define 13 itens de prontidão e os comandos descrevem
como validá-los. Os testes atuais confirmam presença de frases e estruturas, mas
declaram explicitamente que não validam comportamento de runtime.

### 8.3 Resultado esperado

Criar um componente determinístico:

```python
PrReadinessContract.evaluate(context) -> Verdict
```

O contexto deve conter:

- artifact `PR_READY`;
- Build Report;
- Design;
- repositório Git;
- target/base resolvido;
- comandos de teste e build configurados;
- estado atual da branch.

### 8.4 Modelo do artifact

O `PR_READY` deve conter YAML machine-readable além da descrição Markdown:

```yaml
pr_ready:
  schema_version: 1
  feature: WORKFLOW_METRICS
  generated_at: "2026-07-29T..."
  ship_head_sha: "..."
  target_branch: main
  checks:
    working_tree_clean:
      result: pass
      evidence: "git status --short"
    tests:
      result: pass
      command: "python3 -m pytest tests -q"
    branch_verdict:
      result: clean
      source: "BUILD_REPORT..."
```

### 8.5 Validadores

Implementar:

- `PrReadyArtifactContract`: estrutura e campos congelados;
- `PrReadinessRuntimeValidator`: cinco campos mutáveis;
- `PrReadinessCrossArtifactValidator`: coerência com Build Report e Design;
- CLI `spec-lint --phase pr-ready`;
- comando de revalidação usado por `/create-pr`.

### 8.6 Regras mutáveis

Imediatamente antes da publicação:

1. `git status --short` vazio;
2. target/base resolvido;
3. merge-base válido;
4. merge-tree sem conflito;
5. testes reexecutados;
6. build reexecutado quando configurado;
7. HEAD igual ao `ship_head_sha` ou re-review válido posterior;
8. Review Verdict ainda clean/clean-with-minors;
9. zero finding bloqueante aberto.

### 8.7 Tratamento de erro

- erro operacional gera ERROR e bloqueia publicação;
- artifact ausente mantém legacy mode apenas quando explicitamente permitido;
- artifact presente e inválido nunca cai para legacy mode;
- falha gera lista de gaps e não altera Git;
- PR só é publicado após intenção explícita.

### 8.8 Testes obrigatórios

Usar repositórios Git temporários para provar:

- working tree limpo e sujo;
- HEAD igual e divergente;
- base existente e ausente;
- conflito com base;
- testes passando e falhando;
- build configurado e não configurado;
- Review Verdict alterado;
- artifact malformado;
- mais de um `PR_READY`;
- publicação recusada sem intenção explícita;
- cleanup somente após URL confirmada.

### 8.9 Critérios de aceite

- Build, Ship e `/create-pr` usam a mesma implementação;
- os 13 itens possuem validação correspondente;
- nenhum teste depende apenas de substring documental;
- alteração posterior ao Ship invalida prontidão;
- PR inválido nunca é publicado;
- falha preserva branch e artifact.

## 9. Remediação 4 — Consolidar o gate de testes do plugin

### 9.1 Severidade

**High.**

### 9.2 Estado atual

As suítes passam separadamente:

- raiz: 172 testes;
- Spec Linter: 193 testes;
- Spec Judge: 75 testes e 1 skip.

Entretanto:

- `make test` executa somente `tests/`;
- `build-plugin.sh` executa somente `tests/` e paridade;
- uma invocação pytest agregada falha por colisão de módulos
  `test_cli.py` e `test_engine.py`.

### 9.3 Implementação

1. Adicionar `__init__.py` às árvores de testes ou configurar
   `--import-mode=importlib`.
2. Criar target:

```make
test-all:
	python3 -m pytest tests -q
	cd tools/spec-linter && python3 -m pytest -q
	cd tools/spec-judge && python3 -m pytest -q
```

3. Fazer `make test` depender de `test-all`.
4. Fazer `make check` executar:
   - todas as suítes;
   - generator checks;
   - paridade;
   - smoke checks.
5. Fazer `build-plugin.sh` executar as suítes dos componentes antes de apagar e
   regenerar `plugin/`.
6. Se pytest estiver ausente em CI/release, falhar em vez de apenas avisar.
7. Fazer self-check do Spec Judge bloquear quando dependências estão instaladas.
8. Registrar marker `live` para remover warning de configuração.

### 9.4 CI recomendado

Separar jobs para diagnóstico, mantendo um gate agregado:

- `root-tests`;
- `spec-linter-tests`;
- `spec-judge-offline-tests`;
- `plugin-build`;
- `plugin-parity`;
- `adversarial-contract-tests`;
- `release-gate`.

### 9.5 Critérios de aceite

- `make test` executa todas as suítes;
- `make build` não empacota componente com testes falhando;
- não existe erro de import mismatch;
- smoke-check do plugin instalado passa;
- CI apresenta um único resultado bloqueante de release.

## 10. Remediação 5 — Concluir Observe → Warn → Enforce

### 10.1 Severidade

**Medium**, mas necessária para concluir o programa.

### 10.2 Estado atual

- Risk Profile: `observe_warn`;
- Task Manifest: opt-in;
- TDD medium sem evidência: WARN;
- Task Review medium ausente: WARN;
- matriz ausente em high/critical: WARN;
- matriz ausente em medium/low: silent;
- commit/parallel: conduct sem linter;
- PR Readiness: sem linter executável.

### 10.3 Estratégia

Criar uma versão de contrato que diferencie:

```yaml
enforcement_profile:
  artifact_generation:
    new: enforce
    legacy: warn
  risk_profile: enforce
  task_manifest: enforce
  traceability: enforce
  tdd: enforce_by_risk
  task_review: enforce_by_risk
  pr_readiness: enforce
```

### 10.4 Regras para novos artefatos

- todo Define possui Risk Profile;
- todo Design possui manifest v2;
- todo Design possui Traceability Matrix;
- todo Build Report possui schema atual;
- TDD segue risco e tipo de tarefa;
- Task Review segue risco;
- todo Ship produz PR_READY válido ou gap report explícito;
- todo PR criado pelo fluxo revalida PR Readiness.

### 10.5 Compatibilidade legada

Artefato é legado somente quando:

- não possui schema version;
- foi criado antes da versão de enforcement;
- sua origem pode ser demonstrada.

Ausência de campo em artifact novo não pode acionar legacy mode.

### 10.6 Rollout

1. publicar release candidate em Warn;
2. dogfood em pelo menos cinco features;
3. corrigir falsos positivos;
4. congelar schemas;
5. publicar major/minor version de enforcement;
6. manter adaptador legado por janela documentada;
7. medir uso do adaptador antes de removê-lo.

### 10.7 Critérios de aceite

- novos artefatos incompletos falham;
- legados produzem diagnóstico identificável;
- não existe fallback silencioso para novo artifact;
- documentação informa claramente quais regras bloqueiam;
- testes cobrem ambos os perfis.

## 11. Remediação 6 — Unificar parsing e modelos

### 11.1 Severidade

**Medium**, com grande valor preventivo.

### 11.2 Problema

`build_report.py`, `design_phase.py` e outros contratos mantêm regexes, regras de
slug e parsing de tabelas próprios. Correções aplicadas em um parser não chegam
automaticamente aos demais.

### 11.3 Componentes propostos

```text
spec_linter/
├── markdown/
│   ├── document.py
│   ├── headings.py
│   ├── tables.py
│   └── fences.py
├── artifacts/
│   ├── define.py
│   ├── design.py
│   ├── build_report.py
│   └── pr_ready.py
└── contracts/
    ├── define_phase.py
    ├── design_phase.py
    ├── build_report.py
    └── pr_readiness.py
```

### 11.4 Interfaces

```python
document.section_exact("review_verdict")
document.unique_section("traceability_matrix")
table.require_columns([...])
table.require_unique("REQ")
fence.parse_yaml(root="workflow_metrics")
```

### 11.5 Regras de migração

- extrair parser sem mudar severidades inicialmente;
- rodar testes antigos contra as duas implementações;
- comparar findings normalizados;
- migrar um contrato por PR;
- remover helpers antigos somente após paridade.

### 11.6 Critérios de aceite

- uma única implementação de slug;
- uma única implementação de section scoping;
- uma única implementação de tabela;
- findings preservam regra, campo e severidade;
- nenhuma regressão nos artifacts arquivados;
- complexidade dos contratos diminui.

## 12. Remediação 7 — Validação cross-artifact

### 12.1 Objetivo

Validar a cadeia inteira, não apenas cada documento isolado:

```text
DEFINE REQ
→ DESIGN task
→ BUILD execution
→ test evidence
→ Task Review
→ Branch Review
→ SHIPPED
→ PR_READY
```

### 12.2 Regras

- todo REQ MUST do Define aparece no Design;
- toda task do Design aparece no Build Report;
- toda task concluída possui verificação;
- todo teste citado existe ou é comando verificável;
- todo review cita task conhecida;
- todo commit citado pertence ao range da feature;
- SHIPPED resume o mesmo conjunto de requisitos;
- PR_READY não adiciona ou remove requisito;
- métricas reconciliam com as tabelas.

### 12.3 Implementação

Criar:

```python
FeatureBundleContract(
    define,
    design,
    build_report,
    shipped=None,
    pr_ready=None,
)
```

Disponibilizar:

```bash
spec-lint --feature-bundle .claude/sdd/archive/FEATURE/
```

### 12.4 Critérios de aceite

- referência órfã gera finding;
- contagens divergentes geram finding;
- bundle válido recebe PASS;
- Ship executa bundle validation antes do archive final;
- PR Readiness usa o bundle validado.

## 13. Remediação 8 — Hardening de Git e publicação

### 13.1 Objetivo

Garantir que evidência congelada não seja reutilizada após mudanças na branch.

### 13.2 Regras

- target/base deve vir de fonte autorizada pelo ambiente;
- `ship_head_sha` é obrigatório;
- merge-base é recalculado;
- merge-tree usa tip atual da base;
- commit posterior exige nova revisão;
- force-push após Ship invalida artifact;
- working tree sujo bloqueia publicação;
- PR_READY é removido somente depois de URL confirmada;
- falha de `gh` mantém artifact para retry.

### 13.3 Testes

- novo commit após Ship;
- amend do commit;
- rebase;
- base avançando sem conflito;
- base avançando com conflito;
- push falhando;
- criação de PR falhando;
- URL ausente;
- retry idempotente.

## 14. Remediação 9 — Métricas verificáveis

### 14.1 Problema

O schema valida forma e proíbe estimativas evidentes, mas valores podem divergir
das tabelas do próprio relatório.

### 14.2 Melhorias

- `task_count` deve igualar tarefas válidas;
- `fix_rounds` deve igualar Review Verdict e Task Reviews;
- `requirements` deve igualar Traceability Matrix;
- `findings` deve igualar tabelas de review;
- `reopened_tasks` deve apontar IDs;
- `tests_by_type` deve ser derivável da matriz;
- `operational_skips` deve reconciliar com gate ledger;
- `tokens_cost` permanece null+reason quando indisponível.

### 14.3 Critérios de aceite

- métricas fabricadas ou inconsistentes falham;
- valores derivados são gerados, não digitados;
- comparação entre execuções valida schema igual;
- Ship não replica números manualmente.

## 15. Sequência recomendada de pull requests

### PR A — Critical parser bypass

Entrega:

- exact section matching;
- detecção de duplicatas;
- regressões decoy.

Bloqueia todos os demais até merge.

### PR B — Fail-closed tables

Entrega:

- parser estrutural de tabelas;
- erro para linhas truncadas;
- migração das matrizes e Task Reviews.

### PR C — Test-all and release gate

Entrega:

- correção do import mode;
- `make test-all`;
- todas as suítes no build;
- CI agregado.

Pode ser desenvolvido em paralelo ao PR B, depois do PR A.

### PR D — Executable PR Readiness

Entrega:

- modelo;
- contrato;
- runtime validator;
- integração Ship/Create PR;
- testes com Git temporário.

### PR E — Cross-artifact bundle validation

Entrega:

- `FeatureBundleContract`;
- rastreabilidade completa;
- integração com Ship.

### PR F — Parser/model consolidation

Entrega:

- módulos compartilhados;
- migração dos contratos;
- remoção de duplicação.

Pode ser dividido por artifact se o diff ficar grande.

### PR G — Enforcement release

Entrega:

- perfil de enforcement;
- distinção novo/legado;
- migração;
- documentação.

### PR H — Metrics reconciliation and hardening

Entrega:

- métricas derivadas;
- regras de consistência;
- testes do gate de release.

### PR I — Benchmark and release candidate

Entrega:

- benchmark repetido;
- relatório comparativo;
- decisão go/no-go;
- release candidate.

## 16. Dependências

```text
PR A exact sections
    ├── PR B fail-closed tables
    ├── PR C test-all
    └── PR D PR Readiness

PR B + PR D
    └── PR E bundle validation

PR A + PR B
    └── PR F parser consolidation

PR C + PR D + PR E + PR F
    └── PR G enforcement

PR E + PR G
    └── PR H metrics reconciliation

Todos
    └── PR I benchmark/release
```

## 17. Estratégia de testes completa

### 17.1 Unitários

- parser de headings;
- parser de tabelas;
- parser de YAML fences;
- modelos de artefato;
- regras individuais.

### 17.2 Contrato

- valores e seções obrigatórios;
- vocabulários fechados;
- severidades;
- compatibilidade;
- versões.

### 17.3 Integração

- Define → Design;
- Design → Build;
- Build → Ship;
- Ship → PR_READY;
- PR_READY → Create PR.

### 17.4 Adversariais

- decoy headings;
- headings duplicados;
- tabelas truncadas;
- placeholders;
- IDs duplicados;
- referências órfãs;
- metadata fora de seção;
- YAML válido com root incorreto;
- conteúdo válido em seção errada;
- artifact presente, mas inválido.

### 17.5 Git

- repositório temporário;
- branches divergentes;
- conflito;
- working tree sujo;
- commits posteriores;
- re-review;
- falha de publicação.

### 17.6 Regressão

Validar todos os artifacts arquivados e registrar:

- PASS;
- WARN de migração;
- FAIL esperado;
- correção necessária.

## 18. Observabilidade

Cada gate deve registrar:

- contrato e versão;
- artifact e SHA;
- início e duração;
- verdict;
- findings;
- skips e motivo;
- comandos executados;
- status de revalidação;
- versão do plugin.

Não registrar secrets, tokens ou conteúdo sensível.

## 19. Rollback

Cada PR deve ser reversível isoladamente.

- parser novo mantém adapter temporário;
- schema novo é versionado;
- enforcement pode voltar a Warn por configuração versionada;
- Create PR pode voltar ao legacy mode somente quando não há artifact novo;
- nenhum rollback pode converter FAIL em PASS silencioso.

## 20. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Endurecimento quebrar artifacts antigos | Alto | Adapter, fixture e modo legado explícito |
| Parser compartilhado introduzir regressão ampla | Alto | Migração por contrato e comparação de findings |
| PR Readiness duplicar lógica | Alto | Um componente consumido por todos |
| Mais gates degradarem eficiência | Médio | Medir duração e executar por risco |
| Testes adversariais ficarem frágeis | Médio | Fixtures mínimas e assertions por regra |
| Enforcement bloquear casos legítimos | Médio | RC em Warn e dogfooding |
| Métricas continuarem cerimoniais | Médio | Reconciliação com dados derivados |
| Markdown permanecer excessivamente complexo | Médio | YAML machine-readable para artifacts críticos |

## 21. Fora do escopo

- substituir o formato Markdown de todos os documentos;
- trocar o provedor de pull requests;
- remover compatibilidade legada imediatamente;
- exigir rede para testes offline;
- alterar automaticamente políticas a partir de uma execução;
- publicar PR sem intenção explícita;
- reescrever histórico Git automaticamente;
- tornar todo warning bloqueante.

## 22. Gate de release

A release candidate só pode ser aprovada quando:

- reproduções dos dois bypasses retornarem FAIL;
- todas as suítes passarem pelo comando único;
- PR Readiness possuir testes de runtime;
- bundle validation passar;
- artifacts novos estiverem em Enforce;
- artifacts legados produzirem diagnóstico;
- plugin empacotado passar smoke e paridade;
- cinco features reais completarem dogfooding;
- benchmark TaskFlow for repetido.

Metas mínimas do benchmark:

- correção funcional: 100;
- requisitos e planejamento: pelo menos 95;
- testes: pelo menos 95;
- código/manutenibilidade: pelo menos 94;
- revisão e PR: 100;
- eficiência: pelo menos 80;
- tempo total medium risk: no máximo 1,5 vez o baseline anterior.

## 23. Definição de pronto

Esta remediação estará concluída quando:

- seções contratuais forem endereçadas exatamente;
- nenhuma linha contratual for descartada;
- PR Readiness for executável;
- todas as suítes bloquearem o build;
- novos artifacts usarem schemas atuais;
- o bundle completo for validado;
- métricas forem reconciliadas;
- Git for revalidado antes da publicação;
- rollout final estiver em Enforce;
- benchmark e dogfooding sustentarem a decisão de release.

## 24. Primeiro passo

Executar o **PR A — Critical parser bypass**.

É a correção de maior prioridade porque o estado atual permite que um Build
Report com finding Critical aberto receba PASS. Enquanto esse bypass existir,
Gate R, Ship e PR Readiness não podem ser considerados fontes confiáveis de
evidência.
