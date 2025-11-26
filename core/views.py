import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
import pandas as pd
from .models import Faculty, CourseModality
from .forms import UploadFileForm, SimpleSearchForm, ApplyPasswordForm
from rapidfuzz import fuzz, process

ADMIN_PIN = '1205'  # 예제용 하드코드

# -----------------------------
# Helper functions: place these AFTER imports/ADMIN_PIN and BEFORE any view functions
# -----------------------------
def _norm_cell(value):
    """
    엑셀 셀 값(normalize).
    - NaN -> ''
    - 숫자(예: 1205.0) -> '1205' (정수이면 소수점 제거)
    - 문자열 -> strip() 된 문자열 반환
    """
    if pd.isna(value):
        return ''
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        else:
            return str(value)
    return str(value).strip()

def _get_password_from_row(row):
    """
    여러 후보 칼럼명에서 password 값을 찾아 normalize 하여 반환.
    """
    candidates = ['password', 'Password', 'PASSWORD', 'pin', 'PIN', 'pass', 'Pass', 'PIN_code', 'password_code']
    for c in candidates:
        if c in row:
            val = _norm_cell(row.get(c))
            if val != '':
                return val
    for key in row.keys():
        if key and key.strip().lower() in ('password', 'pin', 'pass'):
            val = _norm_cell(row.get(key))
            if val != '':
                return val
    return ''

def _get_reason_from_row(row):
    candidates = ['Reason for Applying', 'Reason', 'reason_for_applying', 'reason', 'Reason_for_Applying']
    for c in candidates:
        if c in row:
            val = _norm_cell(row.get(c))
            if val != '':
                return val
    for key in row.keys():
        if key and key.strip().lower() in ('reason for applying', 'reason', 'reason_for_applying'):
            val = _norm_cell(row.get(key))
            if val != '':
                return val
    return ''

def _parse_bool_cell(value):
    """Convert cell value to boolean if possible. Returns None if unknown/empty."""
    v = _norm_cell(value)
    if v == '':
        return None
    vl = v.strip().lower()
    if vl in ('yes', 'y', 'true', '1', 'apply'):
        return True
    if vl in ('no', 'n', 'false', '0'):
        return False
    return None

# -----------------------------
# 추가/수정할 helper 및 함수 (core/views.py에 아래 블록들 삽입/교체)
# -----------------------------

def _get_field(row, candidates):
    """
    row: dict-like (pandas Series.to_dict())
    candidates: list of possible column header names (case-sensitive first pass)
    반환: normalized string (''이면 없음)
    """
    # 1) 정확한 후보명 우선 탐색
    for c in candidates:
        if c in row:
            val = _norm_cell(row.get(c))
            if val != '':
                return val
    # 2) 키들의 소문자 형태로 비교 (공백/언더스코어 차이 보정)
    lowmap = { (k.strip().lower() if k else ''): k for k in row.keys() }
    for c in candidates:
        key = c.strip().lower()
        if key in lowmap and lowmap[key] is not None:
            val = _norm_cell(row.get(lowmap[key]))
            if val != '':
                return val
    # 3) 보다 유연한 매칭: 후보 단어가 키에 포함되는지 확인
    for key in row.keys():
        if not key:
            continue
        kk = key.strip().lower()
        for c in candidates:
            if c.strip().lower() in kk or kk in c.strip().lower():
                val = _norm_cell(row.get(key))
                if val != '':
                    return val
    return ''



# -----------------------------
# 이후에 index, faculty_upload, 기존의 course_upload (여기를 새 코드로 교체), ...
# -----------------------------

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

# --- course_upload에서 frequency_week, password, reason 등 파싱에 _get_field 사용 ---
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
                df = pd.read_excel(f, dtype=object)
                for _, raw_row in df.iterrows():
                    row = raw_row.to_dict()
                    # Korean_name 찾기
                    kn = _get_field(row, ['Korean_name', 'Korean name', 'korean_name', 'name_kr', 'Name(KR)', 'Name'])
                    if not kn:
                        continue

                    defaults = {
                        'name': _get_field(row, ['Name', 'name', 'Instructor', 'Instructor Name']),
                        'english_name': _get_field(row, ['English_name', 'English name', 'english_name']),
                        'year': _get_field(row, ['Year', 'year']),
                        'semester': _get_field(row, ['Semester', 'semester']),
                        'language': _get_field(row, ['Language', 'language']),
                        'course_title': _get_field(row, ['Course Title', 'Course_Title', 'course_title', 'Title']),
                        'time_slot': _get_field(row, ['Time Slot', 'Time_Slot', 'time_slot']),
                        'day': _get_field(row, ['Day', 'day']),
                        'time': _get_field(row, ['Time', 'time']),
                        # frequency_week을 다양한 후보명에서 찾아 넣음
                        'frequency_week': _get_field(row, ['Frequency(Week)', 'Frequency', 'Frequency (Week)', 'Frequency Week', 'frequency_week']),
                        'course_format': _get_field(row, ['Course format', 'Course_format', 'course_format']),
                    }

                    # password, reason, apply 처리
                    pw = _get_password_from_row(row)
                    if pw != '':
                        defaults['password'] = pw

                    reason = _get_reason_from_row(row)
                    apply_flag = None
                    apply_flag = _get_field(row, ['Apply this semester(Online 70)', 'Apply this semester', 'Apply', 'Apply_this_semester'])
                    if apply_flag != '':
                        apply_flag = _parse_bool_cell(apply_flag)
                    else:
                        apply_flag = None

                    # get_or_create / merge logic (기존 로직 유지)
                    obj, created = CourseModality.objects.get_or_create(korean_name=kn, defaults=defaults)
                    if not created:
                        changed = False
                        for fld, val in defaults.items():
                            if val != '' and getattr(obj, fld, '') != val:
                                setattr(obj, fld, val)
                                changed = True
                        if reason != '':
                            obj.reason_for_applying = reason
                            obj.modified_date = timezone.now()
                            changed = True
                        if apply_flag is not None:
                            obj.apply_this_semester = bool(apply_flag)
                            obj.modified_date = timezone.now()
                            changed = True
                        if 'password' in defaults and defaults.get('password', '') != '':
                            if (obj.password or '').strip() != defaults['password'].strip():
                                obj.password = defaults['password']
                                changed = True
                        if changed:
                            obj.save()
                    else:
                        if reason != '' or apply_flag is not None:
                            if reason != '':
                                obj.reason_for_applying = reason
                            if apply_flag is not None:
                                obj.apply_this_semester = bool(apply_flag)
                            obj.modified_date = timezone.now()
                            obj.save()
                message = 'Course Modality 업로드 및 병합 완료.'
    else:
        form = UploadFileForm()
    return render(request, 'core/course_upload.html', {'form': form, 'message': message})


# 붙여넣을 함수들: course_search, course_apply, course_lookup, course_admin_export
# (core/views.py의 끝에 추가하세요)

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
            pw = form.cleaned_data['record_password'].strip()
            stored_pw = (record.password or '').strip()
            if pw != stored_pw:
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
            pw = form.cleaned_data['record_password'].strip()
            stored_pw = (record.password or '').strip()
            if pw != stored_pw:
                message = '비밀번호가 틀립니다.'
            else:
                shown = True
    else:
        form = ApplyPasswordForm()
    return render(request, 'core/course_lookup.html', {'record': record, 'form': form, 'message': message, 'shown': shown})

# --- course_admin_export: 'Name' 컬럼 제거 (export에서 보이지 않게) ---
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
                    # 'Name' 컬럼 삭제 요청에 따라 제거함
                    'Korean_name': rec.korean_name,
                    'English_name': rec.english_name,
                    'Year': rec.year,
                    'Semester': rec.semester,
                    'Language': rec.language,
                    'Course Title': rec.course_title,
                    'Time Slot': rec.time_slot,
                    'Day': rec.day,
                    'Time': rec.time,
                    'Frequency(Week)': rec.frequency_week,   # rec.frequency_week에 저장된 값이 출력됨
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


