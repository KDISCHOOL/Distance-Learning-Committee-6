import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
import pandas as pd
from .models import Faculty, CourseModality
from .forms import UploadFileForm, SimpleSearchForm, ApplyPasswordForm
from rapidfuzz import fuzz, process

ADMIN_PIN = '1205'  # 예제용 하드코드

def index(request):
    return render(request, 'core/index.html')

def faculty_upload(request):
    message = ''
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            pin = form.cleaned_data['admin_pin']
            if pin != ADMIN_PIN:
                message = '관리자 PIN이 잘못되었습니다.'
            else:
                f = request.FILES['file']
                df = pd.read_excel(f)
                for _, row in df.iterrows():
                    kn = str(row.get('Korean_name', '')).strip()
                    if not kn:
                        continue
                    en = str(row.get('English_name', '') or '').strip()
                    cat = str(row.get('Category', '') or '').strip()
                    email = str(row.get('Email', '') or '').strip()
                    Faculty.objects.update_or_create(
                        korean_name=kn,
                        defaults={'english_name': en, 'category': cat, 'email': email}
                    )
                message = '업로드 및 병합이 완료되었습니다.'
    else:
        form = UploadFileForm()
    return render(request, 'core/faculty_upload.html', {'form': form, 'message': message})

def faculty_enrich_upload(request):
    message = ''
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        df = pd.read_excel(f)
        if 'Korean_name' not in df.columns:
            message = '엑셀에 "Korean_name" 컬럼이 필요합니다.'
        else:
            out_rows = []
            for _, row in df.iterrows():
                kn = str(row.get('Korean_name', '')).strip()
                if not kn:
                    out_rows.append({'No': '', 'Korean_name': '', 'English_name': '', 'Category': '', 'Email': ''})
                    continue
                try:
                    fac = Faculty.objects.get(korean_name=kn)
                    out_rows.append({'No': '', 'Korean_name': kn, 'English_name': fac.english_name, 'Category': fac.category, 'Email': fac.email})
                except Faculty.DoesNotExist:
                    out_rows.append({'No': '', 'Korean_name': kn, 'English_name': '', 'Category': '', 'Email': ''})
            out_df = pd.DataFrame(out_rows)
            out_df.index = range(1, len(out_df) + 1)
            out_df.reset_index(inplace=True)
            out_df.rename(columns={'index': 'No'}, inplace=True)
            buffer = io.BytesIO()
            out_df.to_excel(buffer, index=False)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=faculty_enriched.xlsx'
            return response
    return render(request, 'core/faculty_enrich.html', {'message': message})

def faculty_search(request):
    results = []
    form = SimpleSearchForm(request.GET or None)
    if form.is_valid():
        name = form.cleaned_data['name'].strip()
        qs = Faculty.objects.filter(korean_name__iexact=name) | Faculty.objects.filter(english_name__iexact=name)
        if qs.exists():
            results = list(qs)
        else:
            all_names = list(Faculty.objects.values_list('korean_name', flat=True))
            if all_names:
                match = process.extractOne(name, all_names, scorer=fuzz.ratio)
                if match and match[1] >= 70:
                    try:
                        results = [Faculty.objects.get(korean_name=match[0])]
                    except Faculty.DoesNotExist:
                        results = []
    return render(request, 'core/faculty_search.html', {'form': form, 'results': results})

def course_upload(request):
    message = ''
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            pin = form.cleaned_data['admin_pin']
            if pin != ADMIN_PIN:
                message = '관리자 PIN이 잘못되었습니다.'
            else:
                f = request.FILES['file']
                df = pd.read_excel(f)
                for _, row in df.iterrows():
                    kn = str(row.get('Korean_name', '')).strip()
                    if not kn:
                        continue
                    defaults = {
                        'name': str(row.get('Name', '') or '').strip(),
                        'english_name': str(row.get('English_name', '') or '').strip(),
                        'year': str(row.get('Year', '') or '').strip(),
                        'semester': str(row.get('Semester', '') or '').strip(),
                        'language': str(row.get('Language', '') or '').strip(),
                        'course_title': str(row.get('Course Title', '') or '').strip(),
                        'time_slot': str(row.get('Time Slot', '') or '').strip(),
                        'day': str(row.get('Day', '') or '').strip(),
                        'time': str(row.get('Time', '') or '').strip(),
                        'frequency_week': str(row.get('Frequency(Week)', '') or '').strip(),
                        'course_format': str(row.get('Course format', '') or '').strip(),
                        'password': str(row.get('password', '') or '').strip(),
                    }
                    CourseModality.objects.update_or_create(korean_name=kn, defaults=defaults)
                message = 'Course Modality 업로드 및 병합 완료.'
    else:
        form = UploadFileForm()
    return render(request, 'core/course_upload.html', {'form': form, 'message': message})

def course_search(request):
    form = SimpleSearchForm(request.GET or None)
    results = []
    if form.is_valid():
        name = form.cleaned_data['name'].strip()
        qs = CourseModality.objects.filter(korean_name__iexact=name) | CourseModality.objects.filter(english_name__iexact=name)
        if qs.exists():
            results = list(qs)
        else:
            candidates = list(CourseModality.objects.values_list('korean_name', flat=True)) + list(CourseModality.objects.values_list('english_name', flat=True))
            if candidates:
                match = process.extractOne(name, candidates, scorer=fuzz.ratio)
                if match and match[1] >= 70:
                    results = list(CourseModality.objects.filter(korean_name=match[0]) | CourseModality.objects.filter(english_name=match[0]))
    return render(request, 'core/course_search.html', {'form': form, 'results': results})

def course_apply(request, pk):
    record = get_object_or_404(CourseModality, pk=pk)
    message = ''
    if request.method == 'POST':
        form = ApplyPasswordForm(request.POST)
        if form.is_valid():
            pw = form.cleaned_data['record_password']
            if pw != record.password:
                message = '비밀번호가 틀립니다.'
            else:
                new_reason = request.POST.get('reason_for_applying', '').strip()
                if 'save' in request.POST:
                    if not new_reason:
                        message = 'Reason for Applying(신청 이유)를 입력해야 합니다.'
                    else:
                        record.reason_for_applying = new_reason
                        record.apply_this_semester = True
                        record.modified_date = timezone.now()
                        record.save()
                        message = 'Your application has been saved.'
                if 'cancel' in request.POST:
                    record.apply_this_semester = False
                    record.modified_date = timezone.now()
                    record.save()
                    message = 'Your application has been cancelled.'
                return render(request, 'core/course_apply.html', {'record': record, 'form': form, 'message': message, 'unlocked': True})
    else:
        form = ApplyPasswordForm()
    return render(request, 'core/course_apply.html', {'record': record, 'form': form, 'message': message, 'unlocked': False})

def course_lookup(request, pk):
    record = get_object_or_404(CourseModality, pk=pk)
    message = ''
    shown = False
    if request.method == 'POST':
        form = ApplyPasswordForm(request.POST)
        if form.is_valid():
            pw = form.cleaned_data['record_password']
            if pw != record.password:
                message = '비밀번호가 틀립니다.'
            else:
                shown = True
    else:
        form = ApplyPasswordForm()
    return render(request, 'core/course_lookup.html', {'record': record, 'form': form, 'message': message, 'shown': shown})

def course_admin_export(request):
    message = ''
    if request.method == 'POST':
        pin = request.POST.get('admin_pin', '')
        if pin != ADMIN_PIN:
            message = '관리자 PIN이 잘못되었습니다.'
        else:
            qs = CourseModality.objects.all().order_by('id')
            rows = []
            for rec in qs:
                rows.append({
                    'No': rec.id,
                    'Name': rec.name,
                    'Korean_name': rec.korean_name,
                    'English_name': rec.english_name,
                    'Year': rec.year,
                    'Semester': rec.semester,
                    'Language': rec.language,
                    'Course Title': rec.course_title,
                    'Time Slot': rec.time_slot,
                    'Day': rec.day,
                    'Time': rec.time,
                    'Frequency(Week)': rec.frequency_week,
                    'Course format': rec.course_format,
                    'Apply this semester(Online 70)': 'Yes' if rec.apply_this_semester else 'No',
                    'Reason for Applying': rec.reason_for_applying,
                    'Modified Date': rec.modified_date.isoformat() if rec.modified_date else '',
                    'password': rec.password,
                })
            df = pd.DataFrame(rows)
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=course_modality_export.xlsx'
            return response
    return render(request, 'core/course_admin_export.html', {'message': message})
