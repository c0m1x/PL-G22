# Compilador Fortran 77 → EWVM

**Grupo G22 — Processamento de Linguagens 2026**

| Número | Nome |
|--------|------|
| a107365 | Beatriz Martins Miranda |
| a106927 | Tiago José Pereira Martins |
| a106894 | Francisco Quintas Barros |

---

## Descrição

Compilador para um subconjunto de Fortran 77 com destino à máquina virtual EWVM. Implementado em Python com `ply.lex` e `ply.yacc`, segue uma pipeline completa com representação intermédia (TAC), otimização e geração de código VM.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Utilização

### Compilar um ficheiro Fortran

```bash
python3 src/main.py examples/fatorial.f -o out.vm
```

### Opções disponíveis

```
python3 src/main.py <ficheiro.f> [opções]

  -o OUTPUT       Ficheiro de saída VM (default: out.vm)
  --dump-ast      Mostra a AST
  --dump-ir       Mostra a representação intermédia (TAC)
  --no-opt        Desativa otimizações
  --run           Executa na EWVM após compilar
  --input TEXT    Input para o programa ao usar --run
  --visualize PATH  Gera PDF da AST (requer graphviz)
  --repl          Inicia o REPL interativo
```

### Otimizar IR textual

```bash
python3 src/main.py examples/fatorial.f --dump-ir --no-opt > fatorial.ir
python3 src/optimize.py fatorial.ir -o fatorial.opt.ir
```

### REPL interativo

```bash
python3 src/main.py --repl
```

Modos disponíveis no REPL: `/translate` (default), `/parse`, `/ir`, `/run`, `/visualize`.

## Exemplos

Os 5 exemplos do enunciado estão em `examples/`:

| Ficheiro | Descrição |
|----------|-----------|
| `hello.f` / `hello.vm` | Olá, Mundo! |
| `fatorial.f` / `fatorial.vm` | Cálculo do fatorial |
| `primo.f` / `primo.vm` | Verificação de número primo |
| `somaarr.f` / `somaarr.vm` | Soma de array com READ |
| `conversor.f` / `conversor.vm` | Conversão de base com FUNCTION |

## Testes

```bash
# Suite completa com cobertura
python3 -m pytest

# Sem relatório de cobertura
python3 -m pytest --no-cov -q
```

Estado atual: **125 testes, 74% cobertura**.

## Pipeline de compilação

```
Fortran 77
    ↓ preprocessor.py   (fixed-form: colunas 1-5 label, col 6 continuação, 7-72 código)
Linhas normalizadas
    ↓ lexer.py          (ply.lex — tokens tipados)
Tokens
    ↓ parser.py         (ply.yacc + controlo estrutural por linhas)
AST
    ↓ semantic.py       (tipos, declarações, labels, arrays, subprogramas)
AST anotada
    ↓ ir_gen.py         (lowering para TAC com inlining de subprogramas)
TAC (IR)
    ↓ optimizer.py      (constant folding, copy propagation, dead code elimination, peephole)
TAC otimizado
    ↓ codegen.py        (geração de instruções EWVM)
Código VM
```

## Funcionalidades suportadas

**Tipos:** `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `CHARACTER*n`

**Controlo de fluxo:** `IF/THEN/ELSE/ENDIF`, `DO label ... CONTINUE`, `GOTO`, `GO TO`, `STOP`

**I/O:** `READ`, `PRINT`, `WRITE` (list-directed)

**Operadores:** `+`, `-`, `*`, `/`, `**`, `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`, `.AND.`, `.OR.`, `.NOT.`

**Arrays:** escalares e multidimensionais com índice literal e dinâmico

**Subprogramas** *(valorização)*: `FUNCTION`, `SUBROUTINE`, `CALL`, `RETURN` — tratados por inlining com isolamento de variáveis locais

**Formato de entrada:** fixed-form Fortran 77 (colunas 1-72); aceita também formato livre simples

## Otimizações implementadas

1. *Constant folding* — avalia expressões constantes em tempo de compilação
2. *Copy propagation* — elimina cópias redundantes entre variáveis
3. *Dead temporary elimination* — remove temporários cujo valor nunca é usado
4. *Dead store elimination* — remove escritas sobrescritas antes de serem lidas
5. *Unreachable code elimination* — remove código após saltos incondicionais
6. *Peephole* — elimina `x = x` e saltos para a label imediatamente seguinte

## Arquitetura dos módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| `preprocessor.py` | Normalização fixed-form, labels, continuação |
| `lexer.py` | Tokenização com `ply.lex` |
| `parser.py` | Gramática com `ply.yacc` + blocos estruturais |
| `semantic.py` | Verificação de tipos, declarações, labels, arrays |
| `ir_gen.py` | AST → TAC (com inlining de subprogramas) |
| `optimizer.py` | Passes de otimização sobre TAC |
| `codegen.py` | TAC → instruções EWVM |
| `vm.py` | Interpretador local EWVM (para testes sem rede) |
| `optimize.py` | CLI standalone para otimização de IR textual |
| `ewvm.py` | Interface HTTP com a EWVM remota |
| `visualizer.py` | Geração de PDF da AST (Graphviz) |
| `repl.py` | REPL interativo |
