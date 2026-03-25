from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UploadCSVForm, SelectColumnForm
from .models import UploadedFile
from apps.csv_processor.services import read_csv_columns


def upload_file(request):
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.cleaned_data['file']
            result = read_csv_columns(file)

            if not result.success:
                messages.error(request, result.error_message)
                return render(request, 'core/upload.html', {'form': form})

            uploaded = UploadedFile.objects.create(
                original_name=file.name,
                file=file,
                total_rows=result.total_rows,
            )

            request.session['csv_columns'] = result.columns
            request.session['uploaded_file_id'] = uploaded.id

            messages.success(request, f'Arquivo enviado! {result.total_rows} linhas encontradas.')
            return redirect('core:select_column')
    else:
        form = UploadCSVForm()

    return render(request, 'core/upload.html', {'form': form})


def select_column(request):
    # Recupera os dados da sessão
    columns = request.session.get('csv_columns')
    uploaded_file_id = request.session.get('uploaded_file_id')

    # Se não há sessão, o usuário acessou a página diretamente — manda de volta
    if not columns or not uploaded_file_id:
        messages.warning(request, 'Envie um arquivo CSV primeiro.')
        return redirect('core:upload')

    uploaded = get_object_or_404(UploadedFile, id=uploaded_file_id)

    if request.method == 'POST':
        form = SelectColumnForm(request.POST, columns=columns)

        if form.is_valid():
            selected = form.cleaned_data['column']

            # Salva a coluna escolhida no banco
            uploaded.selected_column = selected
            uploaded.save()

            # Limpa a sessão — não precisamos mais das colunas
            del request.session['csv_columns']

            messages.success(request, f'Coluna "{selected}" selecionada.')
            return redirect('core:process', pk=uploaded.id)
    else:
        form = SelectColumnForm(columns=columns)

    context = {
        'form': form,
        'uploaded': uploaded,
        'columns': columns,
    }
    return render(request, 'core/select_column.html', context)

def process_file(request, pk):
    # Implementaremos na Etapa 5
    uploaded = get_object_or_404(UploadedFile, id=pk)
    messages.info(request, f'Processamento de "{uploaded.original_name}" em breve!')
    return redirect('core:upload')