# Especificação dos achados adicionais da auditoria de remediação

## 1. Contexto

Esta especificação registra problemas encontrados ao verificar
`2026-07-29-agentspec-architecture-remediation-design.md` contra o código em
`3f2cd5b`. Ela cobre somente achados que não estavam descritos de forma
explícita na especificação original.

## 2. Finding N1 — headings opacos eram interpretados como estrutura

### Severidade

High.

### Evidência

`define_phase.py` e `design_phase.py` mantinham scanners locais baseados em
regex. Diferentemente de `spec_linter.sections`, eles não ignoravam headings
dentro de fences Markdown ou comentários HTML. Assim, uma seção contratual
citada como exemplo podia satisfazer presença ou fornecer um YAML que não
pertencia à estrutura viva do documento.

### Correção

- tornar `spec_linter.sections` a autoridade compartilhada para slug, headings
  e limites de seção;
- migrar Define e Design para `heading_slugs()` e `find_sections()`;
- manter somente os endereços explicitamente permitidos
  (`risk_profile[_prospective]` e `task_manifest[_v2]`);
- adicionar regressões com headings dentro de fences.

### Critério de aceite

Conteúdo citado nunca satisfaz nem alimenta uma seção contratual.

## 3. Finding N2 — o comando agregado não isolava os pacotes locais

### Severidade

High.

### Evidência

`python3 -m pytest tools/spec-linter/tests -q` executado na raiz falhava na
coleta com `ModuleNotFoundError: spec_linter`. As suítes só funcionavam quando
executadas a partir dos respectivos diretórios. O repositório não oferecia um
target que encapsulasse essa diferença.

### Correção

- criar `make test-all`;
- executar raiz, Spec Linter e Spec Judge em seus diretórios corretos;
- fazer `make test` depender do gate agregado;
- fazer `make check` reutilizar o mesmo gate;
- fazer o build falhar quando pytest ou uma suíte de componente falhar.

### Critério de aceite

`make test`, `make test-all`, `make check` e `make build` não podem aprovar uma
árvore na qual qualquer uma das três suítes falhe.

## 4. Finding N3 — PR_READY não tinha representação executável

### Severidade

High.

### Evidência

O template possuía apenas tabelas e placeholders. Os testes de raiz verificavam
substrings e o CLI não aceitava `--phase pr-ready`. Portanto, um artifact
incompleto podia ser consumido por instrução sem validação determinística.

### Correção

- adicionar bloco YAML `pr_ready` schema v1 com catálogo congelado de 13 checks;
- implementar `PrReadyArtifactContract`;
- implementar `PrReadinessRuntimeValidator`;
- expor `spec-lint --phase pr-ready --runtime`;
- vincular Ship e Create PR ao comando executável;
- cobrir repositório limpo/sujo, HEAD, base, merge-tree e comandos mutáveis.

### Critério de aceite

Artifact presente e inválido falha; drift mutável bloqueia publicação; falha
preserva o artifact.

## 5. Estado

Os três findings foram corrigidos no mesmo ciclo em que foram especificados.
Sua validação final faz parte do gate agregado descrito no relatório de
auditoria.

## 6. Finding N4 — release podia ser inferida sem evidência empírica

### Severidade

High para release; não bloqueia o uso das correções em desenvolvimento.

### Evidência

Não existia target `release-gate`, nem relatório do benchmark TaskFlow repetido
após a remediação. Os artifacts existentes não provam cinco features de
dogfooding sob o contrato final.

### Correção

`make release-gate` agora executa check/build e falha fechado enquanto não
existirem:

- relatório pós-remediação no caminho versionado;
- decisão explícita Go/No-Go;
- cinco SHIPPED artifacts pós-remediação.

### Estado

O bypass de processo está resolvido: não é mais possível aprovar o gate sem
evidência. A evidência empírica continua pendente e, por definição, não pode ser
fabricada por esta auditoria.

## 7. Finding N5 — gate offline executava teste live quando havia credencial

### Severidade

High para determinismo de CI/release.

### Evidência

Com `OPENROUTER_API_KEY` disponível, `make release-gate` entrou no teste marcado
`live` e ficou bloqueado em I/O TLS. O mesmo comando havia terminado rápido em
ambientes sem a credencial, tornando o gate dependente do ambiente.

### Correção

Os targets agregados, o target do Spec Judge e o build executam explicitamente
`pytest -m "not live"`. Testes live permanecem opt-in e não participam do gate
offline bloqueante.

### Critério de aceite

Credenciais presentes ou ausentes não alteram a seleção da suíte de release.

## 8. Finding N6 — artifacts históricos não formavam bundles de release

### Severidade

High para evidência de release.

### Evidência

Ao aplicar o contrato final aos artifacts arquivados, SHIPPED e Build Reports
anteriores apresentaram conjuntos incompletos ou divergentes de REQ-IDs. Eles
continuam válidos como registro histórico, mas não podem ser promovidos como
dogfood do protocolo final.

### Correção

- preservar os artifacts históricos sem reescrever sua evidência;
- executar cinco validações reais pós-remediação;
- gerar bundles canônicos completos para cada validação;
- exigir identidade, requisitos, tarefas, SHIPPED e PR_READY consistentes no
  gate semântico.

### Critério de aceite

Os cinco bundles de dogfood passam em `--bundle-mode release`; um artifact
histórico incompleto continua falhando, em vez de ganhar compatibilidade
silenciosa.

## 9. Finding N7 — avaliador de navegador assumia labels globalmente únicos

### Severidade

High para a confiabilidade do benchmark.

### Evidência

O primeiro ensaio externo encontrou falsos negativos quando uma interface
correta expunha dois headings válidos, múltiplos campos `description` ou uma
confirmação explícita de exclusão. Os seletores globais do avaliador eram
ambíguos e confundiam acessibilidade rica com falha funcional.

### Correção

- escopar campos e ações ao formulário ou item correspondente;
- aceitar o fluxo seguro de confirmação de exclusão;
- não exigir estado vazio global após remover somente o item criado pelo teste;
- manter asserts independentes para loading, falha de request e acessibilidade.

### Critério de aceite

Os dois cenários Playwright externos passam contra a aplicação, continuam
falhando quando o comportamento contratado é removido e não dependem de uma
estrutura DOM específica.

## 10. Finding N8 — schema de evidência rejeitava repositório isolado versionado

### Severidade

Medium.

### Evidência

`evidence.schema.json` aceitava apenas paths terminados exatamente em
`work2/agentspec` ou `work2/superpowers`. A repetição segura usa um novo
repositório isolado com sufixo, portanto sua evidência válida era rejeitada
pelo schema.

### Correção

Permitir sufixos lowercase/hífen após o nome do framework, preservando a raiz
`work2` e o catálogo fechado de frameworks.

### Critério de aceite

O evidence JSON do run pós-remediação valida sem permitir paths arbitrários.

## 11. Finding N9 — driver declarava isolamento que não configurava

### Severidade

High para novos benchmarks.

### Evidência

O docstring de `session_driver.py` afirmava que cada sessão recebia um
`CLAUDE_CONFIG_DIR` novo, mas `subprocess.run` herdava integralmente o ambiente
do processo pai. O run observado carregou somente o plugin AgentSpec e tinha
memória de projeto vazia, porém o isolamento prometido não era executável.

### Correção

O ensaio confirmou que um `CLAUDE_CONFIG_DIR` vazio também remove a sessão de
autenticação e torna o runner inoperante. O contrato foi corrigido para não
prometer esse isolamento impossível neste ambiente:

- autenticação permanece no profile do usuário;
- `--setting-sources project` exclui settings de usuário;
- exatamente um `--plugin-dir` é passado;
- o evento `init` bruto é retido para auditar a lista efetiva de plugins;
- memória do novo workdir deve estar vazia antes do run.

### Critério de aceite

Todo novo run prova no evento `init` que somente o plugin selecionado foi
carregado, sem depender de uma afirmação não executável sobre autenticação.
