# Benchmark AgentSpec vs. Superpowers: TaskFlow

## Resultado executivo

As duas soluções entregaram uma aplicação correta, persistente, testada, revisada e pronta para pull request. Neste ensaio, o **AgentSpec venceu por margem pequena no resultado agregado (94,6 vs. 93,5)** por chegar ao mesmo resultado funcional em menos da metade da janela de desenvolvimento observada e com planejamento muito mais compacto. O **Superpowers venceu em testes e revisão**: produziu 43 testes de back-end e 42 de frontend, aplicou revisão por tarefa, correções iterativas e revisão final da branch.

Recomendação: AgentSpec para equipes que valorizam fluxo único, documentação de requisitos rastreável e velocidade; Superpowers para mudanças de maior risco em que TDD disciplinado, segregação por tarefa e revisão redundante justificam custo e latência maiores.

O upstream descreve o Superpowers como metodologia completa baseada em skills, com brainstorming, worktree, plano granular, execução por subagentes, TDD, code review e finalização de branch. O comportamento observado correspondeu a essa sequência. [Documentação oficial do Superpowers](https://github.com/obra/superpowers#the-basic-workflow)

## Controle do experimento

- Mesma aplicação e requisitos congelados.
- Claude Code 2.1.220, Sonnet 5 e esforço alto nas duas execuções.
- Repositórios independentes, sem remotes e sem acesso ao resultado concorrente.
- Apenas o plugin avaliado foi carregado em cada sessão.
- Ordem congelada: AgentSpec primeiro, Superpowers depois.
- A pasta `/work2` do sistema não permitia escrita; usou-se o fallback aprovado `~/work2`.
- Nenhum PR foi publicado; cada branch contém `PR.md`.
- Tokens exatos são `unavailable`: a execução interativa não forneceu telemetria comparável.

## Evidência bruta

| Medida | AgentSpec | Superpowers |
|---|---:|---:|
| Janela do primeiro artefato ao `PR.md` | 42m31s | 1h32m38s |
| Commits após `main` | 8 | 26 |
| Artefatos de definição/planejamento | 5 docs, 1.333 linhas | design 173 + plano 3.085 linhas |
| Tarefas explicitamente segregadas | manifesto no DESIGN | 16 tarefas, um implementador e revisor por tarefa |
| Back-end | 32 testes, lint e mypy passam | 43 testes, lint e mypy passam |
| Frontend | 22 testes, lint, tsc e build passam | 42 testes, lint, tsc e build passam |
| E2E | 1 Playwright passa | 1 Playwright passa |
| Revisão | revisão nativa final; 10 achados documentados/corrigidos | revisão incremental; 3 rodadas de correção local + revisão final com 2 commits de correções |
| Estado final | branch limpa + `PR.md` | branch limpa + `PR.md` |
| Warnings | 1 depreciação de dependência | 3 depreciações FastAPI/Starlette |

Todos os comandos acima foram repetidos por fora dos workflows depois do término e passaram. Evidência normalizada: [`agentspec/evidence.json`](runs/agentspec/evidence.json) e [`superpowers/evidence.json`](runs/superpowers/evidence.json).

## Comparação por fase

| Fase | AgentSpec | Superpowers | Veredito |
|---|---|---|---|
| Brainstorming | Documento dedicado de 216 linhas; separou alternativas, escopo e riscos | Design de 173 linhas obtido por brainstorming em seções | Empate; ambos produziram design aprovado |
| Requisitos | DEFINE dedicado, critérios verificáveis e exclusões | Requisitos incorporados ao design e repetidos no plano | AgentSpec: melhor separação e rastreabilidade |
| Planejamento | DESIGN de 568 linhas com arquitetura e manifesto | Plano de 3.085 linhas, caminhos, código completo e passos RED/GREEN | Superpowers é mais executável; AgentSpec é muito mais econômico |
| Segregação | Manifesto e execução por camadas | 16 tarefas; agente novo e revisão independente por tarefa | Superpowers |
| Implementação | Back-end, frontend, E2E e CI em commits por camada | Commits pequenos por tarefa, com ciclos de correção | Superpowers em granularidade; AgentSpec em velocidade |
| Testes | 55 testes totais incluindo E2E | 86 testes totais incluindo E2E | Superpowers |
| Revisão/correção | Revisão nativa encontrou e corrigiu problemas de DB path, wildcard SQL, lifecycle e testes | Revisões encontraram `null` de status, acessibilidade, sincronização de busca; revisão final corrigiu wildcard, UTC e tratamento de erros | Superpowers, por redundância e trilha por tarefa |
| PR | `PR.md` de 122 linhas | `PR.md` de 114 linhas | Empate |

O resultado do Superpowers também confirma a intenção declarada pelo projeto: planos com tarefas pequenas, TDD RED/GREEN/REFACTOR e revisão em dois estágios. [README oficial](https://github.com/obra/superpowers#how-it-works)

## Pontuação

Pesos aprovados: correção 35%, requisitos/planejamento 20%, testes 15%, código 15%, revisão/PR 10%, eficiência 5%.

| Categoria | Peso | AgentSpec | Superpowers |
|---|---:|---:|---:|
| Correção funcional | 35% | 100 | 100 |
| Requisitos e planejamento | 20% | 95 | 88 |
| Testes | 15% | 88 | 98 |
| Código/manutenibilidade | 15% | 90 | 93 |
| Revisão e PR | 10% | 95 | 100 |
| Eficiência | 5% | 88 | 45 |
| **Total ponderado** | **100%** | **94,6** | **93,5** |

Os subscores são julgamentos do avaliador apoiados pelas medidas brutas; não são métricas universais. Nenhum cap foi aplicado, pois ambas iniciam, persistem dados e não têm defeito crítico conhecido.

## Qual performou melhor?

**No benchmark inteiro: AgentSpec, por 1,1 ponto.** O diferencial foi eficiência e uma cadeia de especificação mais compacta. Seu fluxo produziu um pacote coerente de BRAINSTORM → DEFINE → DESIGN → BUILD_REPORT → SHIPPED, terminou cerca de 50 minutos antes e ainda passou por revisão.

**Na execução rigorosa: Superpowers.** Ele produziu mais testes, mais commits atômicos e uma revisão mais profunda. A revisão final encontrou problemas reais que as revisões locais não haviam capturado. Para código regulado, migrações, pagamentos ou mudanças com grande raio de impacto, essa redundância pode valer mais que o custo.

**Ponto de atenção do Superpowers:** um plano de 3.085 linhas para uma aplicação pequena é sobre-especificação. Ele repetiu grandes blocos de código e consumiu muito contexto antes da primeira implementação. A própria documentação oficial diz que seus planos incluem caminhos exatos, código completo e verificação; neste caso, essa característica passou do ponto ótimo. [Workflow oficial](https://github.com/obra/superpowers#the-basic-workflow)

**Ponto de atenção do AgentSpec:** a qualidade final depende mais da revisão concentrada no fim. Ele entregou menos cobertura e menos checkpoints independentes. Além disso, o benchmark é full-stack genérico, enquanto o AgentSpec local tem origem e especialização mais fortes em workflows de dados; isso limita generalização.

## Limitações

- Um único par de execuções não separa efeito da ferramenta de variância estocástica do modelo.
- A ordem foi AgentSpec → Superpowers; aprendizagem do operador pode favorecer a segunda execução.
- Os gates interativos impediram usar o mesmo driver headless; ambas continuaram em PTY supervisionado.
- Tempo mede a janela entre commits de artefato e `PR.md`, não custo puro de inferência.
- Tokens não foram estimados.
- Não houve avaliação humana cega da interface nem teste de carga/segurança.
- Os PRs são artefatos locais; nenhum GitHub PR foi aberto.

## Artefatos

- AgentSpec: `/Users/matheusjericopalhares/work2/agentspec`
- Superpowers: `/Users/matheusjericopalhares/work2/superpowers`
- Brief congelado: [`brief.md`](brief.md)
- Contrato de evidência: [`evidence.schema.json`](evidence.schema.json)
- Revisão deste relatório: [`review.md`](review.md)
