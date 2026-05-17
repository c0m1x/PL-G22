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



```



