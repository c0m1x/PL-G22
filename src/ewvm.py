"""Interface com a EWVM (Extended Web Virtual Machine).

Envia codigo VM gerado pelo compilador para a EWVM e devolve o output
da execucao. O URL base da EWVM e configuravel via variavel de ambiente
EWVM_URL (default: https://ewvm.epl.di.uminho.pt).
"""

import os

import requests
from bs4 import BeautifulSoup

EWVM_URL = os.environ.get("EWVM_URL", "https://ewvm.epl.di.uminho.pt")
_TIMEOUT = 15  # segundos


def _extract_terminal_output(html: BeautifulSoup) -> str:
    """Extrai o texto de output da pagina da EWVM."""
    # O id "terminal" e o contentor principal de output na UI da EWVM.
    term = html.find(id="terminal")
    if term is not None:
        return term.get_text()
    # Fallback para paginas que usem apenas classes no terminal.
    return "".join(el.get_text() for el in html.find_all(class_="terminal"))


def _find_interaction_form(html: BeautifulSoup):
    """Devolve o form de interacao quando o programa fica a aguardar input."""
    for form in html.find_all("form", {"action": "/run"}):
        if form.find("textarea", {"name": "input"}) is not None:
            return form
    return None


def _form_payload(form) -> dict[str, str]:
    """Extrai os campos do form para reenviar numa nova submissao."""
    payload: dict[str, str] = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if name:
            payload[name] = inp.get("value", "")
    for area in form.find_all("textarea"):
        name = area.get("name")
        if name and name not in payload:
            payload[name] = area.get_text() or ""
    return payload


def _input_chunks(input_data: str) -> list[str]:
    if not input_data:
        return []
    chunks = input_data.splitlines(keepends=True)
    return chunks if chunks else [input_data]


def run_code(code: str, input_data: str = "") -> str:
    """Executa codigo VM na EWVM e devolve o output do terminal.

    Args:
        code: Codigo VM (instrucoes EWVM, uma por linha).
        input_data: Dados de stdin a fornecer ao programa (opcional).

    Returns:
        Texto produzido pelo programa na EWVM.

    Raises:
        RuntimeError: Se a EWVM devolver um erro HTTP ou nao estiver acessivel.
    """
    try:
        with requests.Session() as session:
            response = session.post(
                f"{EWVM_URL}/run",
                json={"code": code},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()

            html = BeautifulSoup(response.text, "html.parser")

            # Em programas com READ, a EWVM devolve um form intermedio
            # (code/sessionId/index/input) que precisa de novas submissões.
            chunks = _input_chunks(input_data)
            idx = 0
            while True:
                form = _find_interaction_form(html)
                if form is None or idx >= len(chunks):
                    break

                payload = _form_payload(form)
                payload["input"] = chunks[idx]
                payload.setdefault("terminal", "")
                idx += 1

                response = session.post(
                    f"{EWVM_URL}/run",
                    data=payload,
                    timeout=_TIMEOUT,
                )
                response.raise_for_status()
                html = BeautifulSoup(response.text, "html.parser")

            return _extract_terminal_output(html)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            f"Nao foi possivel ligar a EWVM em {EWVM_URL}. " "Verifica a variavel de ambiente EWVM_URL."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"EWVM devolveu erro HTTP: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Timeout ao contactar a EWVM.") from exc
