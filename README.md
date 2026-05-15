# PL-G22

a106927 - Tiago Jose Pereira Martins  
a107365 - Beatriz Martins Miranda  
a106894 - Francisco Quintas Barros

## Compilador Fortran 77

Compilador em Python com pipeline completo:

1. preprocessamento (fixed-form Fortran 77 e formato livre simples)
2. analise lexica
3. parsing para AST
4. analise semantica
5. geracao de IR (TAC)
6. otimizacao de IR
7. geracao de codigo VM

Projeto de referencia: `PL2026-projeto-plain-nolayout.txt`.

## Como correr

Instalacao:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Compilacao:

```bash
python3 src/main.py example.f -o out.vm
python3 src/main.py example.f --dump-ast --dump-ir
```

Testes:

```bash
python3 -m pytest -q
RUN_EWVM_TESTS=1 python3 -m pytest -q tests/test_ewvm_outputs.py
```

Otimização da IR textual:

```bash
python3 src/main.py examples/hello.f --dump-ir --no-opt > hello.ir
python3 src/main.py opt-ir hello.ir -o hello.opt.ir
```

## Formato de entrada

O compilador aceita o formato `fixed-form` clássico de Fortran 77:

1. colunas 1-5: label opcional;
2. coluna 6: continuação de linha;
3. colunas 7-72: código executável/declarativo.

Tambem aceita um formato livre simples, incluindo programas copiados diretamente do
enunciado, labels no inicio da linha (`20 IF (...) THEN`) e indentacao leve. Assim,
tanto `      PRINT *, 'Ola'` como `PRINT *, 'Ola'` sao aceites.

## Alinhamento com o enunciado (auditoria)

Estado auditado em `15/05/2026`.

Requisitos minimos para aprovacao (nota base):

1. Analise lexica com `ply.lex`: `OK`
2. Analise sintatica com `ply.yacc`: `OK`
3. Analise semantica (tipos, declaracoes, labels): `OK` (com cobertura de testes)
4. Traducao para IR e VM: `OK`
5. Otimizacao sobre IR: `OK`
6. Suite de testes: `OK`

Requisitos tecnicos de linguagem (enunciado):

1. Declaracoes de tipos e variaveis: `OK`
2. Expressoes aritmeticas, logicas e relacionais: `OK`
3. IF-THEN-ELSE, DO com label, `GOTO`/`GO TO`: `OK`
4. I/O basico (`READ`, `PRINT`, `WRITE` list-directed): `OK`
5. Subprogramas (`FUNCTION`, `SUBROUTINE`, `CALL`) para valorizacao: `OK`
6. Exponenciacao (`**`) via lowering de `POW` para VM: `OK`

Observacao importante sobre arrays:

- Leitura/escrita de elementos de array com indices literais e dinamicos funciona.
- O backend gera acessos indiretos para casos como `A(I)` e `A(I,J)`.
- Arrays multidimensionais usam indexacao 1-based e ordem column-major de Fortran.

## Funcionalidades atualmente suportadas

1. `PROGRAM ... END`
2. `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER` e `CHARACTER*n`
3. atribuicoes escalares e de arrays
4. expressoes com precedencia e associatividade (`+`, `-`, `*`, `/`, `**`, `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`, `.AND.`, `.OR.`, `.NOT.`)
5. `IF (...) THEN ... [ELSE ...] ENDIF` e `END IF`
6. `DO label var = start, end [,step] ... label CONTINUE`
7. `GOTO label`, `GO TO label`, `READ`, `PRINT`, `WRITE`, `STOP`
8. arrays multidimensionais com validacao semantica de rank/limites
9. subprogramas externos: `FUNCTION`, `SUBROUTINE`, `CALL`, `RETURN`
10. I/O tipado e com separadores list-directed no backend VM (`INTEGER/LOGICAL` com `ATOI/WRITEI`, `REAL` com `ATOF/WRITEF`, `CHARACTER` com `WRITES`)
11. ciclos `DO` com guarda correta para `step` positivo e negativo
12. funcoes sem argumentos e isolamento de variaveis locais em subprogramas inlinados
13. literais reais com expoente (`1E3`, `1D3`) e strings com apostrofos duplicados

## Arquitetura de modulos

- `src/preprocessor.py`: fixed-form, formato livre simples, labels e continuation
- `src/lexer.py`: tokenizacao com `ply.lex`
- `src/parser.py`: parser com `ply.yacc` para expressoes/linhas e controlo estrutural por linhas
- `src/semantic.py`: verificacao de tipos, declaracoes, labels e arrays
- `src/ir_gen.py`: AST -> TAC
- `src/optimizer.py`: `constant folding`, `copy propagation`, `dead temp elimination`, `peephole`
- `src/codegen.py`: TAC -> VM
- `src/main.py`: pipeline de ponta a ponta

## Testes e qualidade

Suite em `tests/` cobre:

1. preprocessador
2. semantica (erros e casos positivos)
3. requisitos do enunciado
4. arrays multidimensionais
5. otimizacao
6. pipeline smoke
7. regressao de lacunas criticas
8. subprogramas e indices dinamicos de arrays

Estado atual verificado nesta iteracao: `93 passed`.



## Historico de melhorias (alem da base 10)

Evolucao tecnica resumida por etapas, para demonstrar crescimento incremental do projeto:

1. Base minima (`nota 10`): pipeline funcional com lexer (`ply.lex`), parser, semantica, IR, VM e testes base.
2. Consolidacao da linguagem: cobertura robusta de expressoes, controlo de fluxo (`IF`, `DO`, `GOTO`) e validacoes semanticas de labels/tipos.
3. Otimizacao de IR: `constant folding`, `copy propagation`, `dead temp elimination`, `peephole`.
4. Conformidade tecnica do enunciado: migracao do parser para `ply.yacc`.
5. Valorizacao funcional: suporte de subprogramas (`FUNCTION`, `SUBROUTINE`, `CALL`, `RETURN`) com validacao semantica e lowering em IR.
6. Valorizacao de backend: acesso a arrays com indices dinamicos (`A(I)`, `A(I,J)`) no codegen VM usando enderecamento indireto.
7. Qualidade e regressao: suite expandida com testes dedicados a subprogramas e arrays dinamicos.

Resumo: o projeto ja ultrapassa os requisitos minimos e cobre os principais pontos de valorizacao tecnica previstos no enunciado.

## Lacunas para pontuacao maxima

Com a iteracao atual, os pontos tecnicos criticos identificados foram fechados:

1. parser em `ply.yacc`
2. subprogramas (`FUNCTION`, `SUBROUTINE`, `CALL`, `RETURN`)
3. indexacao dinamica de arrays no codegen VM
4. exponenciacao `**` no backend VM
5. validacao semantica reforcada de operadores
6. funcoes sem argumentos
7. isolamento de variaveis locais durante o inlining
8. compatibilidade com formato livre dos exemplos do enunciado
9. `END IF`, `GO TO`, `READ(*,*)` e `WRITE(*,*)`
10. labels reais no `CONTINUE` terminal de ciclos `DO`
11. arrays multidimensionais em ordem Fortran

Para robustez extra de defesa/avaliacao, continua recomendado:

1. execucao regular dos testes EWVM com `RUN_EWVM_TESTS=1`
2. reforco de semantica de argumentos em cenarios avancados de aliasing

## Roadmap tecnico objetivo

1. Fase 1: aumentar cobertura com programas completos do enunciado
2. Fase 2: endurecer validacoes semanticas de subprogramas
3. Fase 3: automatizar validacao end-to-end na VM de referencia
