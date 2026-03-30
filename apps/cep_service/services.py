from .models import CepCache
from .providers import fetch_viacep, fetch_brasilapi, _clean_cep, _is_valid_cep, CepData


# Lista de providers em ordem de prioridade
PROVIDERS = [fetch_viacep, fetch_brasilapi]


def lookup_cep(cep_raw: str) -> CepData:
    """
    Ponto de entrada principal — recebe um CEP em qualquer formato
    e retorna os dados do endereço.

    Fluxo:
    1. Limpa e valida o CEP
    2. Verifica se já está no cache
    3. Se não estiver, tenta cada provider em ordem
    4. Salva o resultado no cache
    5. Retorna os dados
    """
    cep = _clean_cep(cep_raw)

    # Valida antes de qualquer coisa
    if not _is_valid_cep(cep):
        return CepData(
            found=False,
            cep=cep_raw,
            error=f'CEP inválido: "{cep_raw}"'
        )

    # Verifica o cache primeiro
    cached = _get_from_cache(cep)
    if cached is not None:
        return cached

    # Tenta cada provider em ordem
    result = _fetch_from_providers(cep)

    # Salva no cache independente do resultado
    # (inclusive CEPs não encontrados — para não chamar a API de novo)
    _save_to_cache(result)

    return result


def _get_from_cache(cep: str) -> CepData | None:
    try:
        cached = CepCache.objects.get(cep=cep)
        return CepData(
            found=cached.found,
            cep=cached.cep,
            logradouro=cached.logradouro,
            bairro=cached.bairro,
            cidade=cached.cidade,
            estado=cached.estado,
            latitude=cached.latitude,   # ← novo
            longitude=cached.longitude, # ← novo
        )
    except CepCache.DoesNotExist:
        return None


def _save_to_cache(data: CepData):
    CepCache.objects.update_or_create(
        cep=data.cep,
        defaults={
            'logradouro': data.logradouro,
            'bairro':     data.bairro,
            'cidade':     data.cidade,
            'estado':     data.estado,
            'latitude':   data.latitude,   # ← novo
            'longitude':  data.longitude,  # ← novo
            'found':      data.found,
        }
    )

def _fetch_from_providers(cep: str) -> CepData:
    """Tenta cada provider em ordem. Retorna o primeiro resultado válido."""
    for provider in PROVIDERS:
        result = provider(cep)

        if result is not None:
            # Provider respondeu (mesmo que o CEP não exista)
            return result

    # Todos os providers falharam (sem conexão, timeout, etc.)
    return CepData(
        found=False,
        cep=cep,
        error='Não foi possível conectar às APIs de CEP. Tente novamente.'
    )


