from django import forms
import csv
import io


class UploadCSVForm(forms.Form):
    file = forms.FileField(
        label='Arquivo CSV',
        help_text='Tamanho máximo: 10MB. Formatos aceitos: .csv'
    )

    def clean_file(self):
        file = self.cleaned_data['file']

        # Valida extensão
        if not file.name.lower().endswith('.csv'):
            raise forms.ValidationError('O arquivo precisa ter extensão .csv')

        # Valida tamanho
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O arquivo não pode ser maior que 10MB')

        # Valida se o conteúdo é realmente um CSV legível
        try:
            raw = file.read(2048)  # lê só os primeiros 2KB para validar
            try:
                sample = raw.decode('utf-8')
            except UnicodeDecodeError:
                sample = raw.decode('latin-1')

            if not sample.strip():
                raise forms.ValidationError('O arquivo está vazio.')

            # Verifica se tem pelo menos uma linha com conteúdo
            lines = [l for l in sample.splitlines() if l.strip()]
            if len(lines) < 2:
                raise forms.ValidationError(
                    'O arquivo precisa ter pelo menos um cabeçalho e uma linha de dados.'
                )

        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError('Não foi possível ler o arquivo. Verifique se é um CSV válido.')
        finally:
            # Importante: volta o cursor para o início para a view poder ler depois
            file.seek(0)

        return file


class SelectColumnForm(forms.Form):
    column = forms.ChoiceField(
        label='Qual coluna contém os CEPs?',
        help_text='Selecione a coluna que será usada para buscar os endereços'
    )

    def __init__(self, *args, columns=None, **kwargs):
        super().__init__(*args, **kwargs)
        if columns:
            self.fields['column'].choices = [(col, col) for col in columns]