# DLC operation (간단 버전)

간단한 설명:
- Django 기반 (권장 Django 4.2)
- DB: SQLite (기본)
- 주요 앱: core
- 기능:
  - Faculty Email Finder: 엑셀 업로드(관리자 PIN 필요), Korean_name 기준 병합, Korean_name 리스트 업로드 -> 보완된 엑셀 다운로드, 검색 및 이메일 복사
  - Course Modality DB: 엑셀 업로드(관리자 PIN 필요), Korean_name 기준 병합, 검색, Apply with password, Look up user submission, 관리자 엑셀 다운로드
- 관리자 업로드 PIN: 1205 (예제용 하드코드)
- 배포: PythonAnywhere 추천 (README 하단 배포 가이드 참고)

설치(로컬 개발):
1. 가상환경 생성 및 활성화
   python3 -m venv venv
   source venv/bin/activate

2. 의존성 설치
   pip install -r requirements.txt

3. 마이그레이션
   python manage.py migrate

4. 개발 서버 실행
   python manage.py runserver

주의: 학습/테스트용 예제입니다. 실제 운영 시 보안(SECRET_KEY, ADMIN PIN, DEBUG) 설정을 강화하세요.
