# Release gate merge-aware binding

## Contexto

O gate de release vincula a evidência a `release_source_commit` e permite que,
depois desse commit, apenas caminhos de evidência sejam alterados. A
implementação atual usa `git diff release_source_commit HEAD`.

Depois que uma branch é mergeada, `HEAD` também contém alterações que já
estavam no target antes do merge. O diff direto atribui incorretamente essas
alterações da branch-base ao período posterior ao commit-fonte e bloqueia uma
release válida.

## Objetivo

Permitir que o mesmo gate seja executado antes e depois do merge sem aceitar
mudanças funcionais posteriores à validação da release.

## Contrato

O bloco `production_readiness` passa a registrar `target_tip`, um SHA completo
que identifica o commit do target usado durante a validação.

O gate deve:

1. validar que `release_source_commit` e `target_tip` são commits existentes;
2. validar que `release_source_commit` é ancestral de `HEAD`;
3. quando `target_tip` for ancestral de `HEAD`, tratar a execução como
   pós-merge; caso contrário, tratar como pré-merge;
4. identificar mudanças introduzidas no lado da release depois de
   `release_source_commit`;
5. excluir mudanças que já pertenciam ao histórico de `target_tip`;
6. aceitar somente caminhos definidos em `_EVIDENCE_ONLY_PATHS` no conjunto
   restante;
7. falhar fechado quando a topologia não puder ser demonstrada.

O frescor do target aceita dois estados:

- pré-merge: o tip remoto deve ser exatamente `target_tip`;
- pós-merge: o tip remoto pode ser `HEAD` quando contém como ancestrais tanto
  `target_tip` quanto `release_source_commit`.

Qualquer avanço remoto que não seja o `HEAD` validado continua bloqueado. Se
existirem commits posteriores ao merge, seus caminhos também passam pela
política de binding descrita acima.

## Algoritmo

Para determinar os commits posteriores ao source que pertencem à release, o
gate usa a revisão:

```text
release_source_commit..HEAD ^target_tip
```

Os caminhos alterados por esse conjunto são obtidos por diff de commits, não
por um diff agregado entre duas árvores. Isso impede que diferenças já
presentes em `target_tip` sejam classificadas como mudanças posteriores da
release.

Quando `HEAD` ainda é a branch pré-merge, `target_tip` não precisa ser ancestral
de `HEAD`; nesse caso, o gate preserva o comportamento existente e verifica o
diff entre `release_source_commit` e `HEAD`. A validade e o frescor do target
continuam cobertos pelos contratos PR_READY.

## Schema e compatibilidade

`target_tip` é obrigatório no schema versionado de `production_readiness`.
Artefatos antigos sem o campo falham fechado. O relatório de prontidão atual
será atualizado com o target validado `4ecf0976baa23d512a8d99e6813df2fd24630b2d`.

## Testes

Os testes de regressão devem cobrir:

- branch pré-merge contendo somente evidência após o source;
- `HEAD` pós-merge com mudanças legítimas vindas do target;
- mudança funcional real no lado da release após o source;
- mudança funcional feita depois do merge;
- target remoto apontando para o próprio merge validado;
- target remoto avançado sem estar conferido no `HEAD` local;
- `target_tip` inexistente;
- topologia em que o source não é ancestral de `HEAD`.

## Verificação

A implementação só estará concluída quando passarem:

```bash
python3 -m pytest tests/test_release_gate.py -q
make check
make build-release
make release-gate
```

O worktree deve permanecer limpo após o build de release.

## Fora de escopo

- alterar os thresholds do benchmark;
- relaxar a lista de caminhos de evidência;
- mudar os contratos PR_READY;
- publicar novo PR, tag, pacote ou deployment.
