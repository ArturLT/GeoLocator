import csv
import io
from typing import Optional


class CSVReadResult:
    def __init__(
        self,
        success: bool,
        columns: list,
        total_rows: int,
        error_message: Optional[str] = None
    ):
        self.success = success
        self.columns = columns
        self.total_rows = total_rows
        self.error_message = error_message


def _detect_delimiter(sample: str) -> str:
    """
    Tenta detectar o delimitador do CSV.
    Se o Sniffer falhar, conta as ocorrências dos delimitadores mais comuns.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except csv.Error:
        first_line = sample.split('\n')[0]
        candidates = {
            ',': first_line.count(','),
            ';': first_line.count(';'),
            '\t': first_line.count('\t'),
            '|': first_line.count('|'),
        }
        best = max(candidates, key=candidates.get)
        return best if candidates[best] > 0 else ','


def read_csv_columns(file) -> CSVReadResult:
    """
    Lê um arquivo CSV enviado via upload e retorna suas colunas e total de linhas.
    """
    try:
        raw = file.read()
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            content = raw.decode('latin-1')

        # Remove linhas vazias antes de processar
        lines = [line for line in content.splitlines() if line.strip()]
        content_clean = '\n'.join(lines)

        sample = content_clean[:1024]
        delimiter = _detect_delimiter(sample)

        # Primeira leitura — pega as colunas
        reader = csv.DictReader(io.StringIO(content_clean), delimiter=delimiter)
        columns = reader.fieldnames

        if not columns:
            return CSVReadResult(
                success=False,
                columns=[],
                total_rows=0,
                error_message='O arquivo CSV não possui cabeçalho.'
            )

        # Segunda leitura — conta apenas linhas com conteúdo
        second_reader = csv.reader(io.StringIO(content_clean), delimiter=delimiter)
        next(second_reader)  # pula o cabeçalho
        total_rows = sum(1 for row in second_reader if any(cell.strip() for cell in row))

        return CSVReadResult(
            success=True,
            columns=list(columns),
            total_rows=total_rows,
        )

    except csv.Error as e:
        return CSVReadResult(
            success=False,
            columns=[],
            total_rows=0,
            error_message=f'Erro ao ler o CSV: {str(e)}'
        )
    except Exception:
        return CSVReadResult(
            success=False,
            columns=[],
            total_rows=0,
            error_message='Não foi possível processar o arquivo.'
        )


def read_csv_rows(file_path: str) -> tuple[str, list[dict]]:
    """
    Lê o arquivo do disco pelo caminho e retorna o delimitador detectado e as linhas.
    Usado pelo processamento em background — reutiliza a mesma detecção de delimitador.
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Remove linhas vazias
    lines = [line for line in content.splitlines() if line.strip()]
    content_clean = '\n'.join(lines)

    sample = content_clean[:1024]
    delimiter = _detect_delimiter(sample)

    reader = csv.DictReader(io.StringIO(content_clean), delimiter=delimiter)
    rows = list(reader)

    return delimiter, rows