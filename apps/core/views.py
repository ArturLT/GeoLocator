from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UploadCSVForm
from .models import UploadedFile
from apps.csv_processor.services import read_csv_columns


def upload_file(request):
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.cleaned_data['file']

            # Lê as colunas antes de salvar
            result = read_csv_columns(file)

            if not result.success:
                messages.error(request, result.error_message)
                return render(request, 'core/upload.html', {'form': form})

            # Salva o arquivo no banco
            uploaded = UploadedFile.objects.create(
                original_name=file.name,
                file=file,
                total_rows=result.total_rows,
            )

            # Guarda as colunas na sessão para a próxima etapa
            request.session['csv_columns'] = result.columns
            request.session['uploaded_file_id'] = uploaded.id

            messages.success(request, f'Arquivo enviado! {result.total_rows} linhas encontradas.')
            return redirect('core:select_column')

    else:
        form = UploadCSVForm()

    return render(request, 'core/upload.html', {'form': form})

def select_column(request):
    # Implementaremos na Etapa 4
    return render(request, 'core/upload.html', {'form': UploadCSVForm()})