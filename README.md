# PL-G22

a106927 - Tiago José Pereira Martins
a107365 - Beatriz Martins Miranda
a106894 - Francisco Quintas Barros




## Fortran77 Compiler

Versao funcional inicial do compilador com pipeline completo: preprocessamento, analise lexica, parsing para AST, analise semantica, geracao de TAC e codegen VM.

Inclui:

- Estrutura de diretorios (`src/`, etc.)
- `main.py` com pipeline completo e flags (`--dump-ast`, `--dump-ir`, `--no-opt`)
- `preprocessor.py` para formato fixo (colunas 1-72)
- Modulos separados para:
	- lexer (PLY)
	- parser + AST
	- semantica + tabela de simbolos
	- IR (TAC) + otimizacao simples
	- codegen VM
- `requirements.txt`

## Como executar

```bash
python src/main.py exemplo.f -o out.vm
python src/main.py exemplo.f --dump-ast --dump-ir
```

## Cobertura atual

Atualmente o compilador suporta:

- `PROGRAM ... END`
- Declaracoes `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`
- Atribuicoes escalares
- Expressoes aritmeticas/logicas com precedencia (`+`, `-`, `*`, `/`, `**`, `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`, `.AND.`, `.OR.`, `.NOT.`)
- `IF (...) THEN ... [ELSE ...] ENDIF`
- `DO label var = start, end [,step] ... label CONTINUE`
- `GOTO label`, `PRINT *, ...`, `READ *, ...`, `STOP`

## O que ainda falta (proposta completa)

- Subprogramas (`FUNCTION`, `SUBROUTINE`, `CALL`, parametros)
- Integracao com VM externa para testes end-to-end

## Ja implementado nesta iteracao

- Arrays com indexacao multi-dimensional (semantica, IR e codegen para indices literais)
- Otimizacoes TAC adicionais (`constant folding`, `copy propagation`, `DCE`, `peephole`)
- Suite de testes `pytest` expandida com casos de linguagem e edge cases
- Workflow CI em GitHub Actions para execucao automatica de testes

## Proximos passos sugeridos

1. Implementar arrays no semantico + IR + VM
2. Adicionar subprogramas e chamadas
3. Expandir otimizacoes TAC
4. Criar bateria de testes automatica

## Workflow de desenvolvimento e validacao

Fluxo recomendado para garantir regressao zero durante evolucao do compilador:

1. Implementar/ajustar funcionalidade em `src/`
2. Adicionar ou atualizar testes em `tests/`
3. Executar localmente:

```bash
pytest -q
```

4. Abrir `push`/`pull request`; o workflow CI em `.github/workflows/tests.yml`
	executa automaticamente a suite `pytest`