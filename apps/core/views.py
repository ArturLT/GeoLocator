from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from .forms import UploadCSVForm, SelectColumnForm
from .models import UploadedFile, CepResult
from apps.csv_processor.services import read_csv_columns
from apps.cep_service.services import lookup_cep
import csv
import io


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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UploadCSVForm, SelectColumnForm
from .models import UploadedFile, CepResult
from apps.csv_processor.services import read_csv_columns
from apps.cep_service.services import lookup_cep
import csv
import io


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
    columns = request.session.get('csv_columns')
    uploaded_file_id = request.session.get('uploaded_file_id')

    if not columns or not uploaded_file_id:
        messages.warning(request, 'Envie um arquivo CSV primeiro.')
        return redirect('core:upload')

    uploaded = get_object_or_404(UploadedFile, id=uploaded_file_id)

    if request.method == 'POST':
        form = SelectColumnForm(request.POST, columns=columns)
        if form.is_valid():
            selected = form.cleaned_data['column']
            uploaded.selected_column = selected
            uploaded.save()
            del request.session['csv_columns']
            messages.success(request, f'Coluna "{selected}" selecionada.')
            return redirect('core:process', pk=uploaded.id)
    else:
        form = SelectColumnForm(columns=columns)

    return render(request, 'core/select_column.html', {
        'form': form,
        'uploaded': uploaded,
        'columns': columns,
    })


def process_file(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    if uploaded.status == UploadedFile.Status.DONE:
        return redirect('core:results', pk=uploaded.id)

    # Limpa resultados de tentativas anteriores
    uploaded.results.all().delete()

    uploaded.status = UploadedFile.Status.PROCESSING
    uploaded.save()

    try:
        with uploaded.file.open('r') as f:
            content = f.read()

        lines = [line for line in content.splitlines() if line.strip()]
        content_clean = '\n'.join(lines)

        reader = csv.DictReader(io.StringIO(content_clean))
        column = uploaded.selected_column

        results = []
        for i, row in enumerate(reader, start=1):
            cep_raw = row.get(column, '').strip()
            cep_data = lookup_cep(cep_raw)

            results.append(CepResult(
                uploaded_file=uploaded,
                row_number=i,
                cep_original=cep_raw,
                logradouro=cep_data.logradouro,
                bairro=cep_data.bairro,
                cidade=cep_data.cidade,
                estado=cep_data.estado,
                found=cep_data.found,
            ))

        CepResult.objects.bulk_create(results)

        uploaded.status = UploadedFile.Status.DONE
        uploaded.save()

        messages.success(request, f'{len(results)} CEPs processados com sucesso!')
        return redirect('core:results', pk=uploaded.id)

    except Exception as e:
        uploaded.status = UploadedFile.Status.ERROR
        uploaded.save()
        messages.error(request, f'Erro durante o processamento: {str(e)}')
        return redirect('core:upload')
    



def results(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    # Busca todos os resultados do arquivo
    cep_results = uploaded.results.all()

    # Filtro por status (encontrado / não encontrado)
    filter_status = request.GET.get('status', 'all')
    if filter_status == 'found':
        cep_results = cep_results.filter(found=True)
    elif filter_status == 'not_found':
        cep_results = cep_results.filter(found=False)

    # Paginação — 50 resultados por página
    paginator = Paginator(cep_results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estatísticas
    total = uploaded.results.count()
    found = uploaded.results.filter(found=True).count()
    not_found = total - found

    context = {
        'uploaded': uploaded,
        'page_obj': page_obj,
        'filter_status': filter_status,
        'stats': {
            'total': total,
            'found': found,
            'not_found': not_found,
            'percent': round((found / total * 100), 1) if total > 0 else 0,
        }
    }
    return render(request, 'core/results.html', context)

def export_csv(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    # Prepara a resposta como arquivo CSV para download
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="resultado_{uploaded.original_name}"'

    # BOM para o Excel reconhecer UTF-8 corretamente
    response.write('\ufeff')

    writer = csv.writer(response)

    # Cabeçalho
    writer.writerow([
        'cep_original',
        'logradouro',
        'bairro',
        'cidade',
        'estado',
        'encontrado',
    ])

    # Dados
    for result in uploaded.results.all():
        writer.writerow([
            result.cep_original,
            result.logradouro,
            result.bairro,
            result.cidade,
            result.estado,
            'Sim' if result.found else 'Não',
        ])

    return response