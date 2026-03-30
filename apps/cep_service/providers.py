import re
import requests
from typing import Optional
from dataclasses import dataclass


@dataclass  
class CepData:
    """Dados retornados por qualquer provider."""
    found: bool
    cep: str
    logradouro: str = ''
    bairro: str     = ''
    cidade: str     = ''
    estado: str     = ''
    error: str      = ''


def _clean_cep(cep: str) -> str:
    """Remove tudo que não for número do CEP."""
    return re.sub(r'\D', '', cep)


def _is_valid_cep(cep: str) -> bool:
    """CEP brasileiro tem exatamente 8 dígitos."""
    return len(cep) == 8 and cep.isdigit()


def fetch_viacep(cep: str) -> Optional[CepData]:
    """
    Consulta a API ViaCEP.
    Retorna None se houver erro de conexão (para tentar o próximo provider).
    """
    try:
        response = requests.get(
            f'https://viacep.com.br/ws/{cep}/json/',
            timeout=5  # 5 segundos — não trava o sistema se a API demorar
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # ViaCEP retorna {"erro": true} quando o CEP não existe
        if data.get('erro'):
            return CepData(found=False, cep=cep)

        return CepData(
            found=True,
            cep=cep,
            logradouro=data.get('logradouro', ''),
            bairro=data.get('bairro', ''),
            cidade=data.get('localidade', ''),
            estado=data.get('uf', ''),
        )

    except requests.Timeout:
        return None  # deixa o próximo provider tentar
    except requests.ConnectionError:
        return None
    except Exception:
        return None


def fetch_brasilapi(cep: str) -> Optional[CepData]:
    """
    Consulta a API BrasilAPI como fallback.
    Retorna None se houver erro de conexão.
    """
    try:
        response = requests.get(
            f'https://brasilapi.com.br/api/cep/v1/{cep}',
            timeout=5
        )

        if response.status_code == 404:
            return CepData(found=False, cep=cep)

        if response.status_code != 200:
            return None

        data = response.json()

        return CepData(
            found=True,
            cep=cep,
            logradouro=data.get('street', ''),
            bairro=data.get('neighborhood', ''),
            cidade=data.get('city', ''),
            estado=data.get('state', ''),
        )

    except requests.Timeout:
        return None
    except requests.ConnectionError:
        return None
    except Exception:
        return None