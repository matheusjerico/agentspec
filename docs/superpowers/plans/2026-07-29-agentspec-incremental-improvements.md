# Plano incremental de evolução do AgentSpec

> Incorporando o rigor do Superpowers sem perder a eficiência do AgentSpec

## 1. Metadados

| Campo | Valor |
|---|---|
| Status | Pronto para revisão |
| Data | 2026-07-29 |
| Escopo | Evolução incremental do estado atual do AgentSpec |
| Fonte principal | `/Users/matheusjericopalhares/Documents/personal/.superconductor/worktrees/agentspec/sc-cooled-fermion-157c/benchmark/taskflow/report.md` |
| Estratégia | Gap-first, com rastreabilidade por fase e entregas retrocompatíveis |
| Fora do escopo | Reescrever integralmente o workflow ou copiar a metodologia Superpowers |

## 2. Objetivo

Este plano define como evoluir o AgentSpec a partir do estado atual para incorporar
os pontos mais fortes observados no Superpowers: planejamento executável, TDD
disciplinado, tarefas menores, revisões independentes durante a execução, maior
cobertura de testes e uma trilha verificável até o pull request.

A evolução deve preservar as vantagens que fizeram o AgentSpec vencer o benchmark:

- requisitos separados e rastreáveis;
- planejamento compacto;
- menor tempo até a entrega;
- fluxo único de Brainstorm a Ship;
- menor consumo de contexto antes da implementação.

O resultado desejado não é transformar todo desenvolvimento em um processo pesado.
O rigor deve crescer de acordo com o risco da mudança. Funcionalidades simples
continuam rápidas; mudanças críticas recebem TDD obrigatório, revisão independente
e verificações adicionais.

## 3. Evidências e motivação

O benchmark entregou a mesma aplicação com as duas soluções. O AgentSpec obteve
94,6 pontos contra 93,5 do Superpowers e terminou em 42m31s, enquanto o Superpowers
levou 1h32m38s. Entretanto, o Superpowers produziu 86 testes contra 55, usou tarefas
menores e executou revisões incrementais e uma revisão final.

A conclusão prática é:

> O AgentSpec já possui a melhor base de eficiência e rastreabilidade. A lacuna está
> no rigor da execução, especialmente antes da revisão final.

O próprio repositório já avançou desde o benchmark. A feature
`BUILD_QUALITY_GATES`, entregue em 2026-07-29, adicionou:

- revisão adversarial obrigatória da branch ao final do Build;
- `Review Verdict` estruturado;
- ciclo de correção com no máximo duas rodadas;
- Gate R no Autopilot;
- bloqueio do Ship para verdicts `dirty` e `missing`;
- opção `--tdd`;
- tabela de evidências RED/GREEN no Build Report;
- oito testes de contrato documental.

Este documento não replica esse trabalho. Ele parte dele.

## 4. Princípios de implementação

### 4.1 Rigor proporcional ao risco

Nenhum mecanismo caro deve ser obrigatório para toda mudança. Classificação de
risco, critérios objetivos e overrides explícitos determinam o nível de processo.

### 4.2 Contratos executáveis, não apenas instruções

Regras escritas em skills e templates devem possuir validação determinística.
Testes de substring são úteis contra drift documental, mas não substituem testes
do comportamento de gates e transições.

### 4.3 Uma fonte canônica

O diretório `.claude/` é a fonte de verdade; `plugin/` é artefato gerado por
`build-plugin.sh`. Mudanças devem ser feitas primeiro em `.claude/`, validadas e
então empacotadas. Alterações manuais exclusivas em `plugin/` são proibidas, exceto
conteúdo declarado em `plugin-extras/`.

### 4.4 Planejamento executável e econômico

O Design deve dizer exatamente o que executar e verificar, sem incluir
implementações completas. O benchmark mostrou que um plano de 3.085 linhas para
uma aplicação pequena ultrapassa o ponto ótimo.

### 4.5 Evidência antes de declaração

Estados como `Complete`, `Ready for Ship` e `PR Ready` só podem ser produzidos
quando seus critérios possuem evidência identificável.

### 4.6 Compatibilidade progressiva

Artefatos antigos continuam legíveis. Campos novos devem ter defaults seguros ou
uma migração clara. Gates novos entram inicialmente em modo observável antes de
bloquear projetos existentes, exceto quando a segurança exigir falha fechada.

## 5. Estado atual e lacunas

| Capacidade | Estado atual | Lacuna |
|---|---|---|
| Requisitos rastreáveis | Forte | Falta propagação automática até tarefa, teste e PR |
| Classificação de risco | Parcial | Há risk register e halt para CRITICAL, mas não existe perfil que configure o workflow |
| Manifesto de execução | Parcial | Centrado em arquivos; tarefas são inferidas durante Build |
| TDD | Parcial | `--tdd` e evidência existem, mas são opt-in e pouco validados |
| Verificação incremental | Presente | Falta relacionar cada verificação ao requisito e ao risco |
| Revisão por tarefa | Ausente | Revisão adversarial ocorre no final da branch |
| Revisão final | Entregue | Precisa de maior enforcement em runtime e opção cross-model |
| Contrato do Build Report | Parcial | Registrado como `specified target`, ainda não plenamente ligado ao linter |
| Cobertura comportamental | Parcial | Não há matriz obrigatória requisito–teste |
| Commits atômicos | Informal | Não fazem parte do contrato da tarefa |
| PR readiness | Fragmentado | `/create-pr`, Build e Ship não compartilham um contrato único |
| Métricas do workflow | Parcial | Relatórios contêm dados, mas faltam esquema e agregação consistentes |
| Frontend/browser | Lacuna conhecida | Revisões encontraram defeitos que a suíte existente não alcançava |

## 6. Arquitetura-alvo

O workflow permanece com cinco fases. Novos contratos atravessam as fases sem
criar uma sexta fase:

```text
Brainstorm
    ↓ alternativas, riscos iniciais
Define
    ↓ requisitos + perfil de risco
Design
    ↓ grafo de tarefas + matriz de cobertura
Build
    ↓ TDD + verificação + Task Review
    ↓ revisão adversarial da branch
Ship
    ↓ PR Readiness + arquivo + métricas
Pull Request
```

Cinco objetos devem formar a espinha dorsal:

1. `risk_profile`: determina o nível de rigor.
2. `requirement_id`: identifica cada requisito estável.
3. `task_id`: liga requisitos à implementação.
4. `verification_id`: liga tarefas à evidência.
5. `review_finding_id`: liga achados, correções e verdicts.

Esses identificadores devem sobreviver a Define, Design, Build Report, Ship e
descrição do PR.

## 7. Incremento 1 — Consolidar os Build Quality Gates

### 7.1 Problema

O baseline está funcional, mas parte de sua garantia depende de consistência
textual entre Markdown, YAML e templates. O contrato declara Build como
`specified target`, não como binding plenamente ativo.

### 7.2 Implementação

1. Adicionar `required_sections` para `BUILD_REPORT` em
   `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`.
2. Alterar o binding de Build de `specified target` para `wired`.
3. Estender `spec-linter` para validar:
   - presença e valor permitido do Review Verdict;
   - ausência de finding Critical ou Important aberto;
   - consistência entre `Fix rounds used` e o orçamento;
   - evidência TDD quando o modo TDD for obrigatório;
   - tarefas completas antes de status `Complete`.
4. Executar o linter depois de gerar o Build Report e antes do handoff.
5. Definir comportamento para relatórios legados:
   - execução manual: WARN com orientação de migração;
   - Autopilot: `missing` e FAIL bloqueiam;
   - retomada de uma execução antiga: gerar seção de compatibilidade e revisar.
6. Criar teste de paridade entre `.claude/` e `plugin/` após `build-plugin.sh`.
7. Manter testes documentais existentes, mas adicionar testes do motor e dos
   estados de gate.

### 7.3 Áreas afetadas

- `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`
- `.claude/skills/sdd-build/SKILL.md`
- `.claude/skills/sdd-ship/SKILL.md`
- `.claude/skills/sdd-autopilot/SKILL.md`
- `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`
- `tools/spec-linter/spec_linter/contracts/`
- `tools/spec-linter/spec_linter/rules.py`
- `tests/test_build_quality_gates.py`
- novos testes em `tools/spec-linter/tests/`
- `build-plugin.sh`

### 7.4 Critérios de aceite

- Build Report válido recebe PASS do linter.
- `dirty`, `missing` ou finding bloqueante aberto recebe FAIL.
- O Build não declara conclusão se o contrato falhar.
- O Ship recusa o mesmo artefato pelos mesmos motivos.
- O plugin gerado contém exatamente as políticas canônicas relevantes.
- A suíte existente permanece verde.

## 8. Incremento 2 — Perfis de risco

### 8.1 Modelo

Adicionar ao Define:

```yaml
risk_profile:
  level: medium
  reasons:
    - RP-003
  dimensions:
    data_loss: low
    security: medium
    reversibility: low
    blast_radius: medium
    migration: none
  override:
    applied: false
    rationale: null
```

Os níveis são:

- `low`: mudança local, reversível, sem dados sensíveis ou migração;
- `medium`: nova lógica ou integração com impacto limitado;
- `high`: autenticação, autorização, migração, concorrência, PII ou grande raio;
- `critical`: risco plausível de perda irreversível, vazamento de segredo,
  indisponibilidade severa ou ação externa irreversível.

### 8.2 Regras determinísticas

O nível deve ser calculado a partir da maior dimensão aplicável. A skill pode
explicar e sugerir o nível, mas o contrato não deve depender apenas de julgamento
livre do modelo.

Exemplos de elevação automática:

- alteração de autenticação ou autorização: no mínimo `high`;
- migração destrutiva: `critical`;
- escrita em produção sem rollback: `critical`;
- novo endpoint sem dados sensíveis: no mínimo `medium`;
- documentação sem comportamento: normalmente `low`.

Overrides são permitidos, mas exigem autor, justificativa e efeito registrado.
Um override nunca elimina o halt obrigatório de risco CRITICAL.

### 8.3 Efeito do perfil

| Política | Low | Medium | High | Critical |
|---|---|---|---|---|
| TDD | Recomendado | Obrigatório para lógica | Obrigatório | Obrigatório |
| Task Review | Autoavaliação | Seletiva | Independente | Independente + especialista |
| Branch Review | Obrigatória | Obrigatória | Obrigatória | Obrigatória + segunda opinião |
| E2E | Se aplicável | Caminho principal | Caminhos críticos | Caminhos críticos + falhas |
| Segurança | Checklist | Análise dirigida | Review dedicada | Review dedicada e halt |
| Rollback | Opcional | Quando aplicável | Obrigatório | Obrigatório e ensaiado |

### 8.4 Áreas afetadas

- `.claude/skills/sdd-define/SKILL.md`
- `.claude/sdd/templates/DEFINE_TEMPLATE.md`
- `.claude/skills/sdd-design/SKILL.md`
- `.claude/sdd/templates/DESIGN_TEMPLATE.md`
- `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`
- `.claude/skills/sdd-autopilot/SKILL.md`
- `tools/spec-linter/`
- testes de contratos e transições

### 8.5 Critérios de aceite

- Todo Define novo contém um perfil válido.
- Design e Build preservam o nível e suas razões.
- Políticas efetivas são derivadas de modo determinístico.
- Override é visível em todos os relatórios posteriores.
- Artefato legado sem perfil usa `medium` em modo WARN, nunca `low` silencioso.

## 9. Incremento 3 — Manifesto de tarefas executável

### 9.1 Problema

Hoje o Build converte um manifesto de arquivos em tarefas. Essa inferência tardia
reduz a previsibilidade de dependências, testes, commits e delegação.

### 9.2 Formato proposto

O Design deve incluir tarefas compactas:

```yaml
tasks:
  - id: TASK-API-001
    title: Criar endpoint de tarefas
    requirements: [REQ-001, REQ-004]
    depends_on: [TASK-DB-001]
    files:
      create: [backend/app/api/tasks.py]
      modify: [backend/app/main.py]
      tests: [backend/tests/test_tasks_api.py]
    owner: "@python-developer"
    reviewer: "@code-reviewer"
    risk: medium
    execution:
      tdd: required
      parallel_group: api
      commit: "feat(api): add task creation endpoint"
    acceptance:
      - "POST /tasks retorna 201 para payload válido"
      - "payload inválido retorna 422"
    verification:
      red: "pytest backend/tests/test_tasks_api.py -k create -q"
      green: "pytest backend/tests/test_tasks_api.py -q"
      regression: "pytest backend/tests -q"
```

### 9.3 Regras

- Uma tarefa representa uma mudança verificável, não necessariamente um arquivo.
- Cada tarefa de código possui ao menos um requisito e um teste.
- Dependências formam um grafo acíclico.
- Tarefas do mesmo `parallel_group` não podem escrever no mesmo arquivo.
- Código completo não deve ser copiado para o plano.
- O Design deve impor orçamento de tamanho, com justificativa para documentos
  excepcionalmente extensos.

### 9.4 Execução

O Build deixa de inferir tarefas quando o manifesto v2 está presente. Para
manifestos legados, mantém o comportamento atual e registra `manifest_version: 1`.

O executor deve:

1. validar o grafo;
2. determinar tarefas prontas;
3. delegar apenas tarefas sem dependências abertas;
4. executar o ciclo de testes;
5. revisar conforme risco;
6. registrar commit e evidência;
7. liberar tarefas dependentes.

### 9.5 Critérios de aceite

- Ciclos e IDs duplicados bloqueiam Design.
- Conflito de escrita impede paralelismo.
- Nenhuma tarefa é concluída sem seus comandos de verificação.
- Build Report preserva `task_id`, agente, commit, testes e requisitos.
- Manifestos v1 continuam executáveis.

## 10. Incremento 4 — TDD como política verificável

### 10.1 Evolução de `--tdd`

`--tdd` continua disponível como override positivo, mas deixa de ser a única forma
de ativação. O modo efetivo deve ser:

```text
TDD efetivo = flag --tdd OU política de risco OU tarefa marcada required
```

Uma flag futura `--no-tdd` só poderá dispensar tarefas low/medium e deve registrar
justificativa. Não poderá desativar TDD em risco high/critical.

### 10.2 Ciclo por tarefa

1. Criar ou ajustar o teste.
2. Executar RED.
3. Confirmar que a falha corresponde ao comportamento ausente.
4. Implementar a menor mudança correta.
5. Executar GREEN.
6. Refatorar.
7. Executar testes locais e regressão afetada.

Um comando RED quebrado, erro de importação não relacionado ou falha já existente
não conta como evidência.

### 10.3 Exceções

Tarefas documentais, configuração declarativa ou alterações não testáveis usam:

```yaml
tdd_exception:
  reason: non_executable_documentation
  alternative_verification: markdownlint docs/...
  approved_by_policy: true
```

Campos vazios ou `n/a` sem categoria conhecida falham no linter.

### 10.4 Critérios de aceite

- Toda tarefa sujeita a TDD tem RED e GREEN associados ao mesmo comportamento.
- O Build Report diferencia teste novo, regressão e verificação alternativa.
- High/critical não podem dispensar TDD silenciosamente.
- O modo default de projetos legados continua operando com aviso de adoção.

## 11. Incremento 5 — Task Review incremental

### 11.1 Objetivo

Encontrar defeitos antes que eles se acumulem na revisão final, preservando a
revisão de branch como camada independente.

### 11.2 Fluxo

```text
Implementar tarefa
    ↓
Verificar RED/GREEN/regressão
    ↓
Task Review conforme risco
    ↓
Corrigir achados bloqueantes
    ↓
Registrar verdict da tarefa
    ↓
Commit e liberação dos dependentes
```

### 11.3 Escopo da revisão

O revisor recebe:

- requirement IDs;
- critérios de aceite;
- diff da tarefa;
- testes e evidências;
- interfaces dependentes;
- riscos aplicáveis.

Ele não recebe a justificativa detalhada do implementador antes de formar sua
avaliação inicial. Isso reduz confirmação acrítica.

Verdicts por tarefa:

- `clean`;
- `clean-with-minors`;
- `dirty`;
- `skipped-by-policy`.

Critical e Important bloqueiam. Minor pode ser corrigido ou registrado como dívida.
A revisão final deve reavaliar integração, não apenas somar os verdicts locais.

### 11.4 Controle de custo

- low: checklist do executor;
- medium: revisor independente apenas para tarefas de maior risco ou interfaces;
- high: revisor independente para todas as tarefas de código relevantes;
- critical: revisor independente e segunda opinião especializada.

### 11.5 Áreas afetadas

- `.claude/skills/sdd-build/SKILL.md`
- `.claude/agents/workflow/build-agent.md`
- `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`
- `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`
- router de agentes e `code-reviewer`
- `sdd-autopilot`

### 11.6 Critérios de aceite

- Dependentes não iniciam enquanto a tarefa estiver `dirty`.
- Revisor e implementador são distintos quando a política exigir.
- Fix loop por tarefa possui orçamento separado do review final.
- Branch Review permanece obrigatória e registra achados de integração.
- Métricas distinguem defeitos encontrados localmente e apenas no final.

## 12. Incremento 6 — Matriz de rastreabilidade e cobertura

### 12.1 Modelo

Cada requisito MUST e SHOULD deve aparecer numa matriz:

| Requisito | Tarefas | Testes | Tipo | Resultado | Review | PR |
|---|---|---|---|---|---|---|
| REQ-001 | TASK-API-001 | VER-API-001 | Integração | Pass | clean | Incluído |

### 12.2 Regras de cobertura

- MUST sem tarefa: FAIL no Design.
- MUST implementado sem teste: FAIL no Build, salvo exceção contratual.
- SHOULD sem implementação: permitido apenas se explicitamente diferido.
- COULD pode ser removido sem bloquear, mas a decisão deve ser registrada.
- Teste deve apontar para comportamento, não somente para arquivo.

### 12.3 Tipos de verificação

- unitário;
- integração;
- contrato;
- E2E;
- browser/acessibilidade;
- segurança;
- migração/rollback;
- dados/qualidade;
- observabilidade;
- inspeção determinística.

O Design escolhe tipos por requisito e risco. Percentual de linhas pode ser
registrado, mas não substitui cobertura de critérios de aceite.

### 12.4 Frontend e browser

Quando houver interface web, o Design deve detectar o runner existente e exigir:

- ao menos um fluxo E2E para a jornada principal;
- estados de loading, erro e vazio;
- acessibilidade básica;
- comportamento de data/hora no timezone relevante;
- sincronização entre URL, filtro e estado, quando aplicável.

Essa política responde diretamente aos defeitos encontrados nas execuções do
benchmark.

### 12.5 Critérios de aceite

- A matriz é gerada no Design e preenchida no Build.
- O linter detecta IDs órfãos e requisitos sem cobertura.
- Ship confirma cobertura real usando evidências do Build Report.
- A descrição do PR reutiliza a matriz sem reconstrução manual.

## 13. Incremento 7 — Commits, paralelismo e isolamento

### 13.1 Commits

Cada tarefa deve propor uma mensagem Conventional Commit. O Build registra o SHA
quando disponível.

Regras:

- não misturar tarefas independentes no mesmo commit;
- não criar commit com testes falhando, salvo commit RED explicitamente permitido;
- não exigir um commit por arquivo;
- não reescrever histórico sem autorização;
- deixar squash/rebase como decisão do mantenedor.

### 13.2 Paralelismo

O scheduler pode paralelizar somente quando:

- todas as dependências estiverem concluídas;
- os conjuntos de escrita forem disjuntos;
- não houver migração ou contrato compartilhado em disputa;
- o orçamento de agentes permitir;
- a estratégia de merge estiver definida.

Conflitos detectados devem serializar tarefas, não produzir merge automático
arriscado.

### 13.3 Critérios de aceite

- O grafo produz uma ordem determinística.
- Tarefas conflitantes nunca são despachadas em paralelo.
- O relatório liga cada commit à tarefa e às verificações.
- A ausência de Git não bloqueia Build; registra `commit: unavailable`.

## 14. Incremento 8 — PR Readiness Gate

### 14.1 Contrato único

Criar um contrato `pr_readiness` consumido por Build, Ship e `/create-pr`:

```yaml
pr_readiness:
  branch:
    working_tree_clean: true
    base_resolved: true
  quality:
    lint: pass
    types: pass_or_not_configured
    tests: pass
    build: pass_or_not_configured
  traceability:
    must_requirements_covered: true
  review:
    branch_verdict: [clean, clean-with-minors]
    blocking_findings_open: 0
  delivery:
    migration_plan: present_or_not_applicable
    rollback_plan: present_or_not_applicable
    residual_risks: documented
```

### 14.2 Comportamento

- Build produz evidências, mas não abre PR.
- Ship valida o contrato e gera um artefato `PR_READY`.
- `/create-pr` consome esse artefato e revalida condições mutáveis.
- Publicação externa continua exigindo intenção explícita do usuário.
- Falha não destrói trabalho nem altera histórico; produz relatório de lacunas.

### 14.3 Descrição do PR

Gerar:

- problema e solução;
- escopo e fora de escopo;
- requisitos entregues;
- estratégia de teste;
- matriz resumida;
- riscos residuais;
- migração e rollback;
- achados de revisão relevantes;
- instruções de validação;
- screenshots quando aplicável.

### 14.4 Áreas afetadas

- `.claude/commands/workflow/create-pr.md`
- `.claude/skills/sdd-build/SKILL.md`
- `.claude/skills/sdd-ship/SKILL.md`
- `.claude/sdd/templates/SHIPPED_TEMPLATE.md`
- novo template de PR readiness
- `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`
- testes de integração do workflow

### 14.5 Critérios de aceite

- Os três consumidores usam a mesma definição de prontidão.
- Estado mutável é revalidado antes da publicação.
- PR não é aberto automaticamente sem pedido explícito.
- Falha lista ações específicas para alcançar prontidão.

## 15. Incremento 9 — Métricas e melhoria contínua

### 15.1 Métricas mínimas

Registrar por execução:

- duração por fase e tarefa;
- tempo até o primeiro GREEN;
- quantidade de tarefas;
- paralelismo efetivo;
- testes por tipo;
- tarefas reabertas;
- fix rounds locais e finais;
- findings por severidade e etapa;
- requisitos cobertos e excepcionados;
- skips operacionais;
- overrides de risco;
- tokens e custo somente quando a plataforma os fornecer de modo confiável.

### 15.2 Esquema

Criar um bloco machine-readable no Build Report ou um arquivo adjacente:

```yaml
workflow_metrics:
  schema_version: 1
  feature: TASKFLOW
  phase_duration_seconds:
    build: 2551
  review:
    task_findings: 3
    branch_only_findings: 1
  coverage:
    must_total: 8
    must_verified: 8
```

Valores indisponíveis devem ser `null` com `reason`, nunca estimados.

### 15.3 Uso

O Ship resume as métricas e registra lessons learned. A primeira versão não deve
alterar automaticamente políticas. Recalibração automática de risco só deve ser
considerada após múltiplas execuções comparáveis e revisão humana.

### 15.4 Critérios de aceite

- O schema é versionado.
- Métricas ausentes não são fabricadas.
- Build e Ship validam o bloco.
- É possível comparar duas execuções sem analisar prosa.

## 16. Estratégia de testes

Cada incremento deve incluir quatro camadas quando aplicáveis:

### 16.1 Testes unitários

- cálculo do perfil de risco;
- validação do grafo;
- detecção de ciclos e conflito de arquivos;
- regras de TDD;
- cobertura de requisitos;
- avaliação do PR Readiness.

### 16.2 Testes de contrato

- seções e valores permitidos dos templates;
- paridade entre skills, contratos e comandos;
- compatibilidade de versões;
- consistência de budgets;
- IDs e referências.

### 16.3 Testes de integração

Executar fixtures do workflow:

1. low risk e sem TDD obrigatório;
2. medium risk com TDD e review seletiva;
3. high risk com revisor independente;
4. finding Important bloqueando dependente;
5. relatório legado;
6. Build limpo chegando a PR Ready;
7. branch alterada após PR Ready e revalidação falhando.

### 16.4 Dogfooding

Cada feature metodológica deve usar o próprio workflow. Defeitos inseridos
deliberadamente precisam de revisão cega separada para evitar que quem plantou o
erro seja a única pessoa a “descobri-lo”.

## 17. Compatibilidade e rollout

### 17.1 Versionamento

Cada mudança de contrato incrementa a versão de
`WORKFLOW_CONTRACTS.yaml` e adiciona histórico. Templates e relatórios devem
registrar `schema_version`.

### 17.2 Fases de adoção

1. **Observe:** calcular e registrar a nova regra sem bloquear.
2. **Warn:** avisar e explicar a correção.
3. **Enforce:** bloquear novos artefatos.

Risco Critical, secrets, data loss e Review Verdict `dirty/missing` permanecem
fail-closed desde o início.

### 17.3 Artefatos legados

- detectar versão ausente;
- aplicar adaptador documentado;
- nunca fingir que evidência inexistente passou;
- permitir conclusão manual com risco registrado quando a política autorizar;
- oferecer migração idempotente.

## 18. Sequência recomendada de pull requests

### PR 1 — Build Report contract enforcement

Entrega o Incremento 1. É a fundação para que as próximas evidências sejam
confiáveis.

### PR 2 — Risk profiles

Entrega o Incremento 2 com modo Observe/Warn. Não ativa ainda toda a matriz de
rigor.

### PR 3 — Executable task manifest

Entrega o Incremento 3, schema versionado e adaptador v1.

### PR 4 — Risk-driven TDD

Entrega o Incremento 4 e ativa TDD obrigatório por política.

### PR 5 — Incremental Task Review

Entrega o Incremento 5, inicialmente para high/critical; medium entra em Warn.

### PR 6 — Traceability and coverage matrix

Entrega o Incremento 6 e cobertura frontend/browser.

### PR 7 — Commit and parallel execution policy

Entrega o Incremento 7 após o grafo de tarefas estar estável.

### PR 8 — Unified PR Readiness

Entrega o Incremento 8 e integra `/create-pr`.

### PR 9 — Workflow metrics

Entrega o Incremento 9 sem automação adaptativa prematura.

Cada PR deve:

- atualizar fonte em `.claude/`;
- atualizar versão e histórico do contrato;
- incluir testes;
- executar `build-plugin.sh`;
- provar paridade do plugin gerado;
- passar pela revisão adversarial da própria branch;
- registrar compatibilidade e rollout.

## 19. Dependências entre incrementos

```text
Contrato do Build Report
    ├── Perfil de risco
    │      ├── TDD por risco
    │      └── Task Review
    └── Manifesto de tarefas
           ├── Matriz de cobertura
           ├── Commits/paralelismo
           └── Task Review

Todos os anteriores
    └── PR Readiness
           └── Métricas comparáveis
```

Perfil de risco e manifesto podem ser desenvolvidos em branches distintas depois
do PR 1, mas TDD e Task Review dependem da integração de ambos.

## 20. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Workflow ficar tão lento quanto Superpowers | Alto | Perfis de risco e orçamento de contexto |
| Plano voltar a conter código completo | Médio | Limite de tamanho e manifesto declarativo |
| Regras divergirem entre arquivos Markdown | Alto | Contrato executável e testes de paridade |
| Muitos agentes aumentarem inconsistência | Alto | Grafo, ownership de arquivos e review independente |
| TDD virar evidência cerimonial | Alto | Validar causa do RED e vínculo comportamental |
| Compatibilidade quebrar execuções antigas | Alto | Schema versionado, adaptador e rollout gradual |
| Revisões duplicarem custo sem achar defeitos | Médio | Métricas por etapa e política proporcional ao risco |
| PR Ready ficar obsoleto após nova alteração | Alto | Revalidação imediatamente antes da publicação |
| Métricas virarem estimativas não confiáveis | Médio | `null + reason`; proibir inferência |

## 21. Fora do escopo

- substituir GitHub ou o provedor de pull requests;
- publicar PR sem autorização explícita;
- exigir um provedor de modelo específico;
- impor cobertura percentual universal;
- obrigar TDD em documentação pura;
- criar uma nova fase entre Build e Ship;
- reproduzir código completo dentro do Design;
- alterar automaticamente o risco com base em uma única execução;
- tornar todo finding Minor bloqueante.

## 22. Definição de pronto do programa

O programa de melhoria estará concluído quando:

- todo novo Define possuir perfil de risco válido;
- todo Design novo possuir tarefas executáveis e grafo válido;
- requisitos MUST forem rastreáveis até teste e PR;
- TDD for obrigatório e verificável conforme risco;
- revisões por tarefa ocorrerem quando a política exigir;
- revisão final continuar independente e bloqueante;
- Build Report, Ship e PR Readiness forem contratos executáveis;
- artefatos legados tiverem caminho de compatibilidade;
- métricas permitirem comparar rigor, custo e defeitos;
- a versão empacotada não divergir da fonte;
- uma repetição controlada do benchmark preservar correção e reduzir a lacuna de
  testes sem aproximar o tempo do AgentSpec ao do Superpowers.

Meta sugerida para a repetição do benchmark:

- correção funcional: 100;
- requisitos e planejamento: pelo menos 95;
- testes: pelo menos 95;
- código/manutenibilidade: pelo menos 94;
- revisão e PR: 100;
- eficiência: pelo menos 80;
- tempo total: no máximo 1,5 vez o baseline do AgentSpec para risco `medium`.

Essas metas são critérios de engenharia para o experimento, não garantias
universais de desempenho.

## 23. Primeiro passo recomendado

Iniciar pelo **PR 1 — Build Report contract enforcement**.

Antes de adicionar mais rigor, o AgentSpec precisa garantir que o mecanismo já
entregue — Review Verdict, Gate R e TDD Evidence — seja validado por contrato em
runtime. Essa fundação evita construir novas políticas sobre garantias apenas
documentais e oferece o primeiro incremento pequeno, mensurável e reversível.
