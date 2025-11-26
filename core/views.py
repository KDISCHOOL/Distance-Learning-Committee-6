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
                # dtype=object로 읽으면 pandas가 숫자를 자동으로 float로 읽지만 we normalize later
                df = pd.read_excel(f, dtype=object)
                for _, raw_row in df.iterrows():
                    row = raw_row.to_dict()
                    # Korean name 찾아서 병합키로 사용
                    kn = _norm_cell(row.get('Korean_name', ''))
                    if not kn:
                        # try alternative header names
                        for k in row.keys():
                            if k and k.strip().lower() in ('korean_name', 'korean name', 'name_kr', 'name'):
                                kn = _norm_cell(row.get(k))
                                break
                        if not kn:
                            continue

                    # 기본 필드들
                    defaults = {
                        'name': _norm_cell(row.get('Name', '')),
                        'english_name': _norm_cell(row.get('English_name', '')),
                        'year': _norm_cell(row.get('Year', '')),
                        'semester': _norm_cell(row.get('Semester', '')),
                        'language': _norm_cell(row.get('Language', '')),
                        'course_title': _norm_cell(row.get('Course Title', '')),
                        'time_slot': _norm_cell(row.get('Time Slot', '')),
                        'day': _norm_cell(row.get('Day', '')),
                        'time': _norm_cell(row.get('Time', '')),
                        'frequency_week': _norm_cell(row.get('Frequency(Week)', '')),
                        'course_format': _norm_cell(row.get('Course format', '')),
                    }

                    pw = _get_password_from_row(row)
                    if pw != '':
                        defaults['password'] = pw

                    # Reason 및 Apply flag 처리
                    reason = _get_reason_from_row(row)
                    apply_flag = None
                    # 여러 후보 컬럼명 탐색
                    apply_candidates = ['Apply this semester(Online 70)', 'Apply this semester', 'Apply', 'Apply_this_semester', 'Apply_this_semester(Online 70)']
                    for c in apply_candidates:
                        if c in row:
                            apply_flag = _parse_bool_cell(row.get(c))
                            break
                    if apply_flag is None:
                        # 컬럼명이 다를 경우 소문자 기준 매칭
                        for key in row.keys():
                            if key and key.strip().lower() in ('apply this semester', 'apply', 'apply_this_semester', 'apply this semester(online 70)'):
                                apply_flag = _parse_bool_cell(row.get(key))
                                break

                    # 기존 레코드가 있으면 get, 없으면 create
                    obj, created = CourseModality.objects.get_or_create(korean_name=kn, defaults=defaults)
                    if not created:
                        # 기존 레코드는 빈값이 아닌 필드만 덮어쓰기 (의도치 않은 덮어쓰기를 방지)
                        changed = False
                        for fld, val in defaults.items():
                            # defaults may include password
                            if val != '' and getattr(obj, fld, '') != val:
                                setattr(obj, fld, val)
                                changed = True
                        # reason 처리: 업로드된 파일에 reason이 있으면 덮어쓰기 및 modified_date 갱신
                        if reason != '':
                            obj.reason_for_applying = reason
                            obj.modified_date = timezone.now()
                            changed = True
                        # apply flag 처리: 업로드 파일에 값이 있으면 적용/미적용으로 갱신
                        if apply_flag is not None:
                            obj.apply_this_semester = bool(apply_flag)
                            obj.modified_date = timezone.now()
                            changed = True
                        # password 별도 처리 (빈값이면 덮어쓰지 않음)
                        if 'password' in defaults and defaults.get('password', '') != '':
                            if (obj.password or '').strip() != defaults['password'].strip():
                                obj.password = defaults['password']
                                changed = True
                        if changed:
                            obj.save()
                    else:
                        # 새로 생성된 경우, 만약 reason 또는 apply_flag가 존재하면 저장 후 업데이트
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

