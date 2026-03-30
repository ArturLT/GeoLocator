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
    """Função que roda em uma thread separada."""
    from apps.csv_processor.services import read_csv_rows

    uploaded = UploadedFile.objects.get(id=uploaded_id)

    try:
        # Usa o service que já tem detecção de delimitador
        file_path = uploaded.file.path
        delimiter, rows = read_csv_rows(file_path)

        column = uploaded.selected_column

        # DEBUG — remove depois de confirmar
        if rows:
            print(f"Colunas disponíveis: {list(rows[0].keys())}")
            print(f"Linha 1: {rows[0]}")

        results = []
        for i, row in enumerate(rows, start=1):
            cep_raw   = row.get(column, '').strip()
            latitude  = row.get('latitude', '').strip()
            longitude = row.get('longitude', '').strip()
            cep_data  = lookup_cep(cep_raw)

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
            ))

        CepResult.objects.bulk_create(results)
        uploaded.status = UploadedFile.Status.DONE
        uploaded.save()

    except Exception as e:
        import traceback
        print(f"ERRO NO BACKGROUND:\n{traceback.format_exc()}")
        uploaded.status = UploadedFile.Status.ERROR
        uploaded.save()
    except Exception as e:
        import traceback
        print(f"ERRO NO BACKGROUND:\n{traceback.format_exc()}")
        uploaded.status = UploadedFile.Status.ERROR
        uploaded.save()


def process_file(request, pk):
    uploaded = get_object_or_404(UploadedFile, id=pk)

    if uploaded.status == UploadedFile.Status.DONE:
        return redirect('core:results', pk=uploaded.id)

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