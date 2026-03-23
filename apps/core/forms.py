from django import forms

class UploadCSVForm(forms.Form):

    file = forms.FileField(
        label='Arquivo CSV',
        help_text='Tamanho máximo: 10MB', 
    )

    def clean_file(self):
        file = self.cleaned_data['file']

        if not file.name.endswith('.csv'):
            raise forms.ValidationError('O arquivo precisa ser tipor CSV')
        
        if file.size > 10 * 1024 *1024:
            raise forms.ValidationError('O arquivo ultrapasa o limite de 10MB')
        
        return file