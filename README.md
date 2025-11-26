# Distance-Learning-Committee-6
Distance-Learning-Committee-6

# DLC operation (간단 버전)

간단한 설명:
- Django 기반 (Django 4.2 LTS)
- DB: SQLite (기본)
- 주요 앱: core
- 기능:
  - Faculty Email Finder: 엑셀 파일로 교원 DB를 업로드(관리자 PIN 필요), Korean_name 기준 병합, Korean_name 리스트 업로드 -> 상세 항목을 채운 엑셀 다운로드, 이름 검색 후 이메일 복사 버튼
  - Course Modality DB: 엑셀 업로드(관리자 PIN 필요), Korean_name 기준 병합, 검색, Apply this semester(비밀번호 확인 후 Reason 입력/수정/저장), 최종 정보 보기(관리자 PIN)
- 간단 배포: PythonAnywhere 사용 권장

관리자 업로드 PIN: 1205 (하드코드, 예제용)

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

PythonAnywhere 배포 관련 가이드: README 하단 참고

주의: 이 예제는 학습/테스트용입니다. 실제 운영 환경에서는 보안(하드코드 PIN, DEBUG 등)을 강화하세요.
