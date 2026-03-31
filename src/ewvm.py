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
    payload: dict = {"code": code}
    if input_data:
        payload["input"] = input_data

    try:
        response = requests.post(
            f"{EWVM_URL}/run",
            json=payload,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            f"Nao foi possivel ligar a EWVM em {EWVM_URL}. "
            "Verifica a variavel de ambiente EWVM_URL."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"EWVM devolveu erro HTTP: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Timeout ao contactar a EWVM.") from exc

    html = BeautifulSoup(response.text, "html.parser")
    return "".join(el.text for el in html.find_all(class_="terminal"))
