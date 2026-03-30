import re
import requests
from typing import Optional


class CepData:
    """Dados retornados por qualquer provider."""
    def __init__(
        self,
        found: bool,
        cep: str,
        logradouro: str = '',
        bairro: str = '',
        cidade: str = '',
        estado: str = '',
        latitude: str = '',
        longitude: str = '',
        error: str = ''
    ):
        self.found = found
        self.cep = cep
        self.logradouro = logradouro
        self.bairro = bairro
        self.cidade = cidade
        self.estado = estado
        self.latitude = latitude
        self.longitude = longitude
        self.error = error


def _clean_cep(cep: str) -> str:
    """Remove tudo que não for número do CEP."""
    return re.sub(r'\D', '', cep)


def _is_valid_cep(cep: str) -> bool:
    """CEP brasileiro tem exatamente 8 dígitos."""
    return len(cep) == 8 and cep.isdigit()


def fetch_coordinates(logradouro: str, cidade: str, estado: str) -> tuple[str, str]:
    if not cidade:
        print("fetch_coordinates: cidade vazia, abortando")
        return '', ''

    try:
        query = ', '.join(filter(None, [logradouro, cidade, estado, 'Brasil']))
        print(f"fetch_coordinates: query='{query}'")

        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': query,
                'format': 'json',
                'limit': 1,
            },
            headers={'User-Agent': 'CepFinder/1.0'},
            timeout=5
        )

        print(f"fetch_coordinates: status={response.status_code}")
        print(f"fetch_coordinates: resposta={response.text[:200]}")

        if response.status_code != 200:
            return '', ''

        data = response.json()
        if not data:
            print("fetch_coordinates: nenhum resultado encontrado")
            return '', ''

        lat = data[0].get('lat', '')
        lon = data[0].get('lon', '')
        print(f"fetch_coordinates: lat={lat}, lon={lon}")
        return lat, lon

    except Exception as e:
        print(f"fetch_coordinates: ERRO={e}")
        return '', ''


def fetch_viacep(cep: str) -> Optional[CepData]:
    try:
        response = requests.get(
            f'https://viacep.com.br/ws/{cep}/json/',
            timeout=5
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get('erro'):
            return CepData(found=False, cep=cep)

        logradouro = data.get('logradouro', '')
        cidade     = data.get('localidade', '')
        estado     = data.get('uf', '')

        lat, lon = fetch_coordinates(logradouro, cidade, estado)

        return CepData(
            found=True,
            cep=cep,
            logradouro=logradouro,
            bairro=data.get('bairro', ''),
            cidade=cidade,
            estado=estado,
            latitude=lat,
            longitude=lon,
        )

    except requests.Timeout:
        return None
    except requests.ConnectionError:
        return None
    except Exception:
        return None


def fetch_brasilapi(cep: str) -> Optional[CepData]:
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

        logradouro = data.get('street', '')
        cidade     = data.get('city', '')
        estado     = data.get('state', '')

        lat, lon = fetch_coordinates(logradouro, cidade, estado)

        return CepData(
            found=True,
            cep=cep,
            logradouro=logradouro,
            bairro=data.get('neighborhood', ''),
            cidade=cidade,
            estado=estado,
            latitude=lat,
            longitude=lon,
        )

    except requests.Timeout:
        return None
    except requests.ConnectionError:
        return None
    except Exception:
        return None