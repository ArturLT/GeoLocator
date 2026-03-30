import csv
import io
import threading

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse

from .forms import UploadCSVForm, SelectColumnForm
from .models import UploadedFile, CepResult
from apps.csv_processor.services import read_csv_columns
from apps.cep_service.services import lookup_cep


def upload_file(request):
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():

            # Limita a 5 arquivos processando ao mesmo tempo
            processando = UploadedFile.objects.filter(
                status=UploadedFile.Status.PROCESSING
            ).count()
            if processando >= 5:
                messages.error(
                    request,
                    'Muitos arquivos sendo processados. Aguarde e tente novamente.'
                )
                return render(request, 'core/upload.html', {'form': form})

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


def _processar_em_background(uploaded_id):
    from apps.csv_processor.services import read_csv_rows
    import os

    uploaded = UploadedFile.objects.get(id=uploaded_id)

    try:
        # Verifica se o arquivo ainda existe no disco
        if not os.path.exists(uploaded.file.path):
            uploaded.status = UploadedFile.Status.ERROR
            uploaded.save()
            return

        file_path = uploaded.file.path
        delimiter, rows = read_csv_rows(file_path)
        column = uploaded.selected_column

        # Verifica se a coluna ainda existe no arquivo
        if rows and column not in rows[0]:
            uploaded.status = UploadedFile.Status.ERROR
            uploaded.save()
            return

        results = []
        for i, row in enumerate(rows, start=1):
            cep_raw  = row.get(column, '').strip()
            cep_data = lookup_cep(cep_raw)

            results.append(CepResult(
                uploaded_file=uploaded,
                row_number=i,
                cep_original=cep_raw,
                logradouro=cep_data.logradouro,
                bairro=cep_data.bairro,
                cidade=cep_data.cidade,
                estado=cep_data.estado,
                latitude=cep_data.latitude,
                longitude=cep_data.longitude,
                found=cep_data.found,
                error_message=cep_data.error,  
            ))

        CepResult.objects.bulk_create(results)
        uploaded.status = UploadedFile.Status.DONE
        uploaded.save()

    except Exception as e:
        uploaded.status = UploadedFile.Status.ERROR
        uploaded.save()

def process_file(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    if uploaded.status == UploadedFile.Status.DONE:
        return redirect('core:results', pk=uploaded.id)

    # Se está processando há mais de 30 minutos, considera travado e reprocessa
    if uploaded.status == UploadedFile.Status.PROCESSING:
        from django.utils import timezone
        from datetime import timedelta
        limite = timezone.now() - timedelta(minutes=30)
        if uploaded.updated_at > limite:
            # Ainda está dentro do tempo — vai para a página de aguarde
            return redirect('core:aguarde', pk=uploaded.id)
        # Passou do tempo — marca como erro e reprocessa
        uploaded.status = UploadedFile.Status.ERROR
        uploaded.save()

    uploaded.results.all().delete()
    uploaded.status = UploadedFile.Status.PROCESSING
    uploaded.save()

    thread = threading.Thread(
        target=_processar_em_background,
        args=(uploaded.id,)
    )
    thread.daemon = True
    thread.start()

    return redirect('core:aguarde', pk=uploaded.id)
def aguarde(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    if uploaded.status == UploadedFile.Status.DONE:
        return redirect('core:results', pk=uploaded.id)

    if uploaded.status == UploadedFile.Status.ERROR:
        messages.error(request, 'Erro durante o processamento.')
        return redirect('core:upload')

    return render(request, 'core/aguarde.html', {'uploaded': uploaded})


def results(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    cep_results = uploaded.results.all()

    filter_status = request.GET.get('status', 'all')
    if filter_status == 'found':
        cep_results = cep_results.filter(found=True)
    elif filter_status == 'not_found':
        cep_results = cep_results.filter(found=False)

    paginator = Paginator(cep_results, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total     = uploaded.results.count()
    found     = uploaded.results.filter(found=True).count()
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

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="resultado_{uploaded.original_name}"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'cep_original',
        'logradouro',
        'bairro',
        'cidade',
        'estado',
        'latitude',
        'longitude',
        'encontrado',
    ])

    for result in uploaded.results.all():
        writer.writerow([
            result.cep_original,
            result.logradouro,
            result.bairro,
            result.cidade,
            result.estado,
            result.latitude,
            result.longitude,
            'Sim' if result.found else 'Não',
        ])

    return response