from django import forms


class UploadCSVForm(forms.Form):
    file = forms.FileField(
        label='Arquivo CSV',
        help_text='Tamanho máximo: 10MB'
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('O arquivo precisa ter extensão .csv')
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O arquivo não pode ser maior que 10MB')
        return file


class SelectColumnForm(forms.Form):
    column = forms.ChoiceField(
        label='Qual coluna contém os CEPs?',
        help_text='Selecione a coluna que será usada para buscar os endereços'
    )

    def __init__(self, *args, columns=None, **kwargs):
        super().__init__(*args, **kwargs)
        if columns:
            # Monta as choices dinamicamente a partir das colunas do CSV
            self.fields['column'].choices = [(col, col) for col in columns]