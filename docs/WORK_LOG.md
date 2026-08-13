# PostgreSQL Upgrade Brief Generator 실제 작업 기록

## 1. 기록 규칙

- 계획 기준은 `docs/PROJECT_PLAN.md`이다.
- 각 작업은 같은 계획 ID로 기록한다.
- 상태는 `대기`, `진행`, `완료`, `차단`, `재작업` 중 하나를 사용한다.
- 명령을 실행했다는 사실만으로 완료하지 않고 계획서의 완료 조건을 충족해야 완료로 표시한다.
- 비밀정보와 개인키 내용은 기록하지 않는다.

## 2. 계획 대비 현황

| 계획 ID | 계획 항목 | 상태 | 실제 결과 | 차이/문제 | 다음 작업 |
|---|---|---|---|---|---|
| P00 | 문서 및 Git 기준선 | 완료 | 계획서·작업기록·제외규칙 작성 및 GitHub `main` 동기화, 기준 커밋 `38215ae` | 없음 | 변경마다 기록과 동기화 유지 |
| P01 | VM 안정화 | 완료 | NTP·서울 시간대·OS 업데이트·재부팅·SSH 검증 완료, UFW 수신 기본 차단 및 OpenSSH만 허용, `/opt/what_changes_postgresql` 확정 | SSH 비밀번호 인증은 활성 상태이나 현재 P01 완료 조건 범위 밖 | P02 진행, SSH 추가 강화는 별도 작업으로 관리 |
| P02 | 컨테이너 실행 기반 | 완료 | Docker Engine·Compose 설치, 전역 로그 제한·live-restore 적용, 내부 네트워크·볼륨·healthcheck·자원 제한·재부팅 자동 복구 실증 | 운영 서비스가 아직 없어 실제 운영 네트워크·볼륨은 P04에서 생성됨 | P04 애플리케이션·DB 골격 진행 |
| P03 | 로컬 Ollama 벤치마크 | 대기 | 공식 `0.32.9` 비root Docker 서비스와 전용 모델 구성, 강화 짧은 v2/v3 시험 완료 | v3도 97.43초로 속도 기준 실패, AI 우선순위를 마지막으로 변경 | P04~P10 비AI 기반 완료 후 재개 |
| P04 | 애플리케이션 골격 | 완료 | Django·PostgreSQL·관리자 인증·staff 권한 분리·상태 점검·감사 로그 검증 완료 | 실제 관리자 계정과 HTTPS 보안 플래그는 화면 공개 단계에서 적용 | P05 완료 후 P06 진행 |
| P05 | 공식 문서 수집기 | 완료 | PostgreSQL 9 이상 346건 수집·파싱, 자동 실행, 보존·실패격리·무결성 검증 완료 | 안정적인 최신 5개 메이저 감시 방식으로 구현 | P06 버전 비교 엔진 진행 |
| P06 | 버전 비교 엔진 | 완료 | 버전 범위·메이저/minor·beta/RC·공식 지원상태/EOL·변경유형 후보 구현 및 검증 | 유형은 규칙 기반 검수 후보이며 확정 판정 아님 | P08 원문 중심 조회 화면 진행 |
| P07 | AI 및 OmniRoute | 대기 | 라우팅 순서만 확정 | 비AI 데이터 기반보다 후순위 | P04~P10 완료 후 진행 |
| P08 | 검수 및 고객 화면 | 진행 | 비AI 원문 비교·필터·승인/반려·수정 이력·고객/DBA 승인본 구현 및 검증 | AI 요약 대조 칸은 P07과 함께 마지막에 연결 | P09 출력 구현 후 AI 단계에서 최종 완료 판정 |
| P09 | 출력 문서 | 진행 | 승인 항목 전용 5종 출력, 고객·프로젝트 프로필과 로고 결합, 한글 문서 시각 검증 완료 | HTTPS 클립보드와 Word 데스크톱 최종 검증 미구현 | 프록시·HTTPS 단계에서 완료 판정 |
| P10 | 운영과 복구 | 진행 | 외부경로 강제 백업·체크섬, 격리된 빈 환경 전체 복원, health timer와 VM 재부팅 자동복구 검증 | 실제 외부 저장소와 외부 알림 미정 | 외부 저장소·알림 채널 확정 |
| P11 | 시범 검증과 출시 | 대기 | 미착수 | 없음 | P00~P10 이후 진행 |

### 2026-08-13 / P04 / Django·PostgreSQL 최소 실행 골격

사전 고지:

- AI 작업을 중단하고 공식 PostgreSQL 자료 수집 기반을 먼저 구성한다고 알림.
- Docker Compose 실행과 검증은 Mac이 아닌 VM에서만 수행한다고 알림.
- Redis·Valkey·Celery를 사용하지 않고 단일 VM에 맞게 Django 관리 명령과 systemd timer를 사용하기로 확정.

구성:

- Django `5.2.15` LTS, Gunicorn `26.0.0`, psycopg `3.3.4`.
- PostgreSQL `18.4` 컨테이너와 영구 명명 볼륨.
- Django 기본 인증·관리자 기능, DB 연동 상태 점검 URL, 읽기 전용 감사 로그 관리 화면.
- Ollama는 `ai` Compose profile로 분리하고 실행 중이던 컨테이너는 중지. 모델과 설정은 보존.

VM 검증 결과:

```text
Django system check: issues 0
Django test: 1 passed
PostgreSQL: 18.4
DB/web container: healthy
health response: HTTP 200, database up
호스트 공개 포트: 없음
DB 중지 시 health response: HTTP 503, database down
DB 재기동 후 감사 로그 시험 레코드: 1건 보존
```

계획 대비 판정:

- 완료: Django·PostgreSQL 실행, 마이그레이션, DB 장애 감지, 재기동 후 데이터 유지.
- 남음: 실제 수집 데이터 모델에 맞춘 관리자 역할 분리와 로그인 실증.
- P04는 `진행` 상태를 유지하고 P05 데이터 모델과 함께 남은 권한 항목을 마무리함.

### 2026-08-13 / P05 / 공식 릴리스 원문 수집 1차 검증

사전 고지:

- PostgreSQL 공식 도메인의 릴리스 인덱스와 개별 문서만 수집한다고 알림.
- 먼저 18.4 한 건으로 저장과 중복 방지를 확인한 뒤 9.2.10과 18.0으로 버전 규칙을 확인한다고 알림.

구성:

- `release`, `source_snapshot`, `job_run` 데이터 모델과 관리자 조회 화면.
- 공식 HTTPS 도메인 강제, 원문 HTML·추출 텍스트·SHA-256·HTTP 메타데이터·수집시각 저장.
- 원문 HTML을 PostgreSQL DB와 `source_snapshots` 명명 볼륨에 함께 보관.
- 동일 릴리스와 동일 SHA-256 조합에 DB 유일성 제약 적용.
- Django 관리 명령 `sync_releases` 구현.

VM 검증 결과:

```text
18.4 1차: created=1, unchanged=0, failed=0
18.4 2차: created=0, unchanged=1, failed=0
18.4 원문 파일: 48,455 bytes, SHA-256 일치
9.2.10: minor, release date 2015-02-05
18.0: major, release date 2025-09-25
호스트 공개 포트: 없음
```

발견 및 조치:

- 내부 전용 backend 네트워크만으로는 공식 사이트 DNS 조회가 불가능했음.
- DB는 backend에만 유지하고 Django에만 비공개 outbound 네트워크를 추가해 해결.
- 수집 명령의 `--version`이 Django 기본 옵션과 충돌하여 `--release`로 변경.
- 두 문제 모두 실제 수집 전후 검증에서 발견했으며 잘못된 원문 데이터는 생성되지 않음.

계획 대비 판정:

- 완료: 공식 릴리스 인덱스 접근, 원문/해시/URL/수집시각 보관, 재수집 중복 방지, 구버전과 최신 버전 수집.
- 남음: 전체 인덱스 수집, 계층형 변경 항목 파싱, 실패 격리 실증, systemd timer 등록.

### 2026-08-13 / P05 / PostgreSQL 9 이상 최초 백필

사전 고지:

- 공식 인덱스 560건을 매일 전부 요청하지 않고 일일 수집과 최초 백필 범위를 분리한다고 알림.
- 최초 백필은 요구 사례를 포함하는 PostgreSQL 9 이상으로 제한하고 요청 간 0.75초 간격을 적용한다고 알림.

수행:

- PostgreSQL 9 이상 공식 릴리스 346건 순차 수집.
- 네트워크 오류와 5xx 응답에 최대 3회 지수형 재시도 추가.
- 일일 수집은 최신 5개 메이저의 최신 릴리스만 자동 선택하도록 구성.
- 중복 실행 방지와 매일 04:00 KST 실행을 위한 systemd unit/timer 파일 작성 및 문법 검증.
- DB 메타데이터와 볼륨의 원문 파일을 전수 대조하는 `verify_snapshots` 관리 명령 추가.

최종 결과:

```text
공식 인덱스 전체: 560건
PostgreSQL 9 이상 백필 대상: 346건
백필 결과: created=336, unchanged=10, failed=0
DB release: 346건
DB current snapshot: 346건
원문 파일: 346건, 총 10,916,349 bytes
누락 파일: 0
SHA-256 불일치: 0
현재본 중복: 0
릴리스 날짜 누락: 0
일일 선택: 18.4, 17.10, 16.14, 15.18, 14.23
Django test: 6 passed
web/db: healthy
호스트 공개 포트: 없음
```

남은 일:

- 릴리스 노트의 섹션과 변경 항목을 계층형 데이터로 파싱.
- 파싱 실패 격리 시험.
- root 권한으로 검증된 systemd unit/timer를 설치하고 실제 예약 실행 상태 확인.

### 2026-08-13 / P05 / 자동수집 등록과 전체 계층 파싱

자동수집 검증:

```text
timer enabled/active: yes
첫 실행 result: success, exit 0
첫 실행 수집: discovered=5, created=0, unchanged=5, failed=0
다음 실행: 2026-08-14 04:23:59 KST
```

계층 파싱:

- 최신 문서의 `h2/h3/h4` 구조와 구버전 문서의 `h1/h2` 구조를 논리 레벨로 정규화.
- 섹션 제목·부모 계층·목록 밖 본문과 최상위 변경 항목·원문 HTML·SHA-256 저장.
- 대표 검증: 18.4는 섹션 3/항목 74, 18.0은 섹션 30/항목 218, 9.2.10은 섹션 3/항목 69.
- 전체 346개 파싱 성공 후 재실행에서 346개 모두 unchanged 확인.

전체 결과:

```text
파싱 원문: 346
파싱 성공: 346
파싱 오류: 0
섹션: 1,562
변경 항목: 15,521
섹션 없는 릴리스: 0
변경 항목 없는 릴리스: 0
```

계열별 릴리스 수:

```text
9.0=24, 9.1=25, 9.2=25, 9.3=26, 9.4=27, 9.5=26, 9.6=25
10=24, 11=23, 12=23, 13=24, 14=24, 15=19, 16=15, 17=11, 18=5
```

자동 처리 보완:

- 일일 수집 성공 후 `parse_releases`가 이어서 실행되도록 systemd service 원본을 갱신.
- 갱신된 unit을 `/etc/systemd/system`에 재설치한 뒤 실제 연속 실행을 재검증해야 함.

최종 자동 실행 및 완료조건 검증:

```text
자동 연속 실행: sync success → parse success
sync: discovered=5, created=0, unchanged=5, failed=0
parse: discovered=346, parsed=0, unchanged=346, failed=0
원문 변경 테스트: 이전/현재 스냅샷 2건 보존, 현재본 1건
실패 격리 테스트: 정상 릴리스 저장, 실패 릴리스 격리, job status partial
전체 자동 테스트: 9 passed
```

P05 완료 판정:

- 재수집 중복 없음.
- 모든 346개 릴리스에 공식 URL, 원문, 원문 파일, SHA-256 존재.
- 파싱 실패는 릴리스별 오류와 job run으로 격리됨.
- 원문 변경 시 이전 스냅샷을 삭제하지 않고 새 현재본을 생성함.
- 매일 최신 5개 메이저 수집 후 전체 미파싱 원문 파싱이 자동 실행됨.

### 2026-08-13 / P04 / 관리자 인증과 권한 분리 완료

검증 결과:

```text
익명 사용자: 관리자 로그인 화면으로 이동
일반 사용자: 관리자 화면 접근 거부
staff 사용자: 관리자 화면 접근 성공
전체 자동 테스트: 10 passed
DB 장애 시 health: HTTP 503
정상 시 health: HTTP 200
재기동 후 데이터 유지: 확인
```

판정:

- P04 완료조건을 충족해 상태를 `완료`로 변경.
- 운영 관리자 계정은 관리자 화면을 실제로 공개할 때 생성함.
- Django deploy check의 HTTPS 관련 경고 4개는 프록시·인증서가 없는 현재 단계에서는 의도된 상태이며 P09에서 해결함.

### 2026-08-13 / P06 / 버전 비교 엔진 완료

버전 규칙:

- PostgreSQL 9.x는 앞의 두 숫자를 메이저 계열로 해석.
- PostgreSQL 10 이상은 첫 숫자를 메이저 계열로 해석.
- AS-IS는 제외하고 다음 릴리스부터 TO-BE까지 포함.
- 역방향, 동일 버전, 수집되지 않은 버전은 차단.
- beta/RC는 정렬을 지원하지만 기본 비교에서는 제외하고 명시 옵션에서만 포함.

공식 지원정보:

- PostgreSQL 공식 versioning 표의 계열·현재 minor·지원 여부·최초/최종 릴리스일 수집.
- 원문 HTML과 SHA-256을 별도 스냅샷으로 보관하고 동일 원문 재수집 시 중복 방지.
- 공식 표 29개 계열 저장, 현재 지원 계열 14~18 확인.

변경유형 후보:

- AI 없이 명시적 영어 원문 표현으로 `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`, `other` 후보 분류.
- 설명 본문의 단어로 오분류되지 않도록 선행 동사 중심의 `rules-2` 적용.
- `Fix failure to remove...`와 `obsolete row versions` 오분류 사례를 fixed로 교정하고 회귀 테스트 추가.
- 후보 유형과 적용 규칙·규칙 버전을 각 변경 항목에 기록.

`9.2.10 → 18.4` 실제 검증:

```text
포함 릴리스: 286
메이저 릴리스: 13
minor 릴리스: 273
prerelease: 0
섹션: 1,219
변경 항목: 13,110
added: 1,919
changed: 757
deprecated: 19
removed: 431
fixed: 5,977
security: 573
other: 3,434
AS-IS 9.2 지원: 종료, final release 2017-11-09
TO-BE 18 지원: 지원 중, final release 2030-11-14
```

최종 검증:

```text
Django tests: 17 passed
Migration drift: 없음
릴리스 원문 누락/해시 불일치: 0
지원표 원문 누락/해시 불일치: 0
web/db: healthy
```

자동 처리 원본은 `sync_releases → sync_version_support → parse_releases → classify_changes` 순서로 갱신함. 서버 systemd unit 재설치 후 연속 실행을 최종 확인해야 함.

### 2026-08-13 / P08 / 비AI 원문 비교·검수 화면

자동 처리 체인 재검증:

```text
sync_releases: success, 5 unchanged, 0 failed
sync_version_support: success, snapshot unchanged
parse_releases: success, 346 unchanged, 0 failed
classify_changes: success, 처리 대상 0
다음 timer: 2026-08-14 04:16:39 KST
```

화면 기능:

- 로그인 필수 AS-IS/TO-BE 선택 화면.
- 포함 릴리스·메이저·섹션·변경 항목과 AS-IS/TO-BE 공식 지원상태 표시.
- 변경유형·공식 문서 분야 필터 및 50건 단위 페이지 조회.
- 모든 항목에서 PostgreSQL 공식 원문의 해당 섹션으로 이동.
- 내부 검토, 고객용 승인본, DBA용 승인본 보기 수준.
- 고객용/DBA용 보기에서는 승인된 항목만 조회.
- 승인 문구는 원문을 변경하지 않고 별도 필드로 보관.

권한과 이력:

- 일반 로그인 사용자는 조회만 허용하고 승인 POST는 HTTP 403.
- staff만 승인·반려·대기 처리가 가능.
- 상태 변경마다 이전/신규 상태, 수정 문구, 메모, 담당자, 시각을 이력으로 보관.
- 동일 작업을 기본 감사 로그에도 기록.

VM 검증:

```text
Django tests: 23 passed
운영 비교 9.2.10→18.4: release 286
fixed + Changes 필터: 5,885건, 첫 페이지 50건
공식 원문 링크: 확인
익명 사용자: /admin/login/으로 이동
운영 임시 사용자: 삭제 후 0명
web/db: healthy
원문 무결성 오류: 0
```

남은 일:

- P09 일반 텍스트·Markdown·HTML·DOCX·PDF 출력.
- P07 AI 요약을 마지막에 연결한 뒤 원문/AI 요약 대조 기능 최종 판정.

## 3. 상세 작업 기록

### 2026-08-12 / P00 / GitHub 연결 확인

사전 고지:

- 지정 GitHub 저장소의 SSH 접근과 원격 상태를 확인한다고 알림.

수행:

- GitHub 전용 Ed25519 키로 계정 인증 확인.
- `git@github.com:CHOI-Young-Joon/what_changes_postgresql.git` 원격 조회.
- 원격 저장소가 비어 있음을 확인.
- 로컬 작업 폴더를 `main` 브랜치로 초기화.
- `origin` 등록.
- 저장소별 `core.sshCommand`로 GitHub 전용 키 사용 설정.

검증 결과:

- GitHub 계정 인증 성공.
- 원격 조회 성공.
- 로컬 `origin` fetch/push URL 정상.
- 계획 ID `P00`부터 `P11`까지 계획서와 작업 기록의 1:1 대응 확인.
- 비밀정보, 로컬 모델, DB, 생성 문서의 Git 제외 규칙 확인.

남은 일:

- 기준 문서를 커밋 `38215ae`로 GitHub `main`에 push 완료.

### 2026-08-12 / P01 / VM 사전 점검

사전 고지:

- CPU, 메모리, 디스크, OS, 네트워크, sudo, 도구와 업데이트 상태를 읽기 전용으로 점검한다고 알림.

실제 확인값:

```text
OS: Ubuntu 26.04 LTS
Kernel: Linux 7.0.0-29-generic
CPU: 4 vCPU, AMD Ryzen 5 3600 기반
RAM: 15GiB
Swap: 4GiB
Disk: 96GB root, 84GB available
IP: 10.65.50.99/24
Gateway: 10.65.50.1
DNS: 8.8.8.8
SSH: port 22
sudo: password required
```

외부 연결 확인:

- PostgreSQL 공식 문서 HTTP 200.
- Docker Ubuntu 26.04 저장소 HTTP 200.
- GitHub API HTTP 200.
- Docker Registry의 인증 필요 응답 HTTP 401 정상.

발견 사항:

- Chrony는 실행 중이지만 NTP source에 도달하지 못함.
- `Leap status: Not synchronised`.
- 약 50개 OS 업데이트가 대기 중.
- Docker, Node.js, PostgreSQL은 아직 설치되지 않음.

결론:

- 외부 AI API 기반 MVP 운영 자원은 충분.
- NTP 해결과 업데이트가 설치보다 먼저 필요.
- CPU-only 로컬 LLM은 별도 벤치마크 후 결정.

### 2026-08-12 / P01 / 외부 NTP 및 서울 시간대 설정

사전 고지:

- 외부 NTP 연결 상태, Chrony 구성과 VirtualBox 시간 서비스 충돌 여부를 먼저 확인한다고 알림.
- `rock` 계정은 sudo 비밀번호 입력이 필요하므로 사용자가 시간대 변경 명령 한 건만 직접 실행하고, 이후 상태는 원격으로 검증한다고 알림.

점검 결과:

- Chrony가 Canonical Ubuntu 외부 NTP 서버와 동기화 중.
- VirtualBox Guest Additions 시간 동기화 서비스는 설치 또는 실행되어 있지 않음.
- 초기 부팅 중 동기화 실패 기록은 있었지만 점검 시점에는 `System clock synchronized: yes`와 `Leap status: Normal` 상태.

수행:

- 시스템 시간대를 `Etc/UTC`에서 `Asia/Seoul`로 변경.
- 외부 NTP source 설정은 정상 동작 중이어서 불필요하게 변경하지 않음.

검증 결과:

```text
Local time: 2026-08-12 17:31:12 KST
Universal time: 2026-08-12 08:31:12 UTC
Time zone: Asia/Seoul (KST, +0900)
System clock synchronized: yes
NTP service: active
Chrony leap status: Normal
System time offset: 약 1ms
/etc/localtime: /usr/share/zoneinfo/Asia/Seoul
RTC in local TZ: no (UTC 유지, 정상)
```

판정:

- 외부 시간 동기화와 서울 시간대 적용 완료.
- 이후 OS 업데이트와 재부팅 검증까지 완료함. 아래 기록 참조.

### 2026-08-12 / P01 / OS 업데이트와 재부팅 검증

사전 고지:

- 패키지 목록 갱신, 업그레이드 시뮬레이션, 전체 업그레이드, 재부팅, 부팅 후 검증 순서로 진행한다고 알림.
- 작업에 필요한 명령만 허용하는 임시 `sudoers` 규칙을 사용하고 완료 후 삭제한다고 알림.

수행:

- `apt-get update`로 패키지 목록 갱신.
- 시뮬레이션에서 업그레이드 51개, 제거 0개, 단계적 배포 보류 2개 확인.
- `apt-get -y full-upgrade` 실행.
- APT 이력에서 작업 시작 `17:39:30 KST`, 정상 종료 `17:40:09 KST` 확인.
- VM 1회 재부팅.
- 업데이트용 임시 파일 `/etc/sudoers.d/what_changes_postgresql-update` 삭제.
- 구형 커널 패키지는 장애 시 롤백을 위해 자동 제거하지 않음.

재부팅 검증 결과:

```text
이전 boot ID: 3f5a27b8-02f1-4145-9180-4e02b9aa4e32
새 boot ID:   c51cfa62-b544-4de4-ace6-ebd33b49751c
Kernel:       7.0.0-29-generic
IP:           10.65.50.99/24
Gateway:      10.65.50.1
SSH:          active
Failed units: 0
미설정 패키지: 0
Disk:         96GB 중 16GB 사용, 76GB 가용
Memory:       15GiB 중 약 14GiB 가용
Swap:         4GiB 중 0 사용
```

패키지 판정:

- 업그레이드 후 설치/설정이 덜 끝난 패키지는 없음.
- `python3-software-properties`, `software-properties-common` 2개는 Ubuntu phased update 정책에 따라 보류됨. 실패가 아니므로 강제 설치하지 않음.
- 재부팅 요구 파일은 없었지만 업데이트 후 실제 부팅과 서비스 복구를 검증하기 위해 계획대로 한 번 재부팅함.

시간 동기화 재검증:

- VirtualBox 재부팅 직후 게스트 시계가 약 `460.640초` 느려 Chrony가 한 차례 step 보정함.
- 보정 후 시스템 시각과 RTC는 UTC 기준으로 일치하고, 시스템 시간대는 `Asia/Seoul`로 유지됨.
- 다음 NTP 표본에서 `System time` 약 `0.605ms`, `Last offset` 약 `0.613ms`, `Leap status: Normal` 확인.
- 현재 운영에는 문제가 없지만 향후 재부팅 검증에서 초기 RTC 오차의 반복 여부를 관찰함.

계획 대비 판정:

- 완료: OS 업데이트와 재부팅, 공개키 SSH 재접속, Chrony 동기화, 네트워크/DNS, 실패 서비스 0건 검증.
- 이후 방화벽과 공개 포트 정책, 서버 애플리케이션 디렉터리까지 확정함. 아래 기록 참조.

### 2026-08-12 / P01 / 방화벽과 애플리케이션 경로 확정

사전 고지:

- 현재 리슨 포트, UFW 상태, SSH 유효 설정과 디렉터리 현황을 먼저 읽기 전용으로 확인한다고 알림.
- 기존 SSH 접속을 보호하기 위해 OpenSSH 허용을 먼저 확인한 후 UFW를 활성화한다고 알림.
- 적용 후 완전히 새로운 SSH 세션, 외부 HTTPS와 NTP를 검증한다고 알림.

점검 결과:

- 외부 인터페이스 리슨 포트는 `22/tcp` 하나였음.
- DNS `53`과 Chrony 명령 포트 `323/udp`는 루프백 주소에만 바인딩됨.
- UFW 패키지와 부팅 서비스는 존재했지만 실제 방화벽 상태는 `inactive`였음.
- 저장된 UFW 사용자 규칙은 `OpenSSH` 허용 하나였음.
- SSH 유효 설정은 `Port 22`, 공개키 인증 활성, 비밀번호 인증 활성, root 비밀번호 로그인 금지 상태였음.

수행:

- UFW에서 `OpenSSH` 허용 규칙 재확인.
- 기본 수신 정책을 `deny`, 기본 송신 정책을 `allow`, routed 정책을 `disabled`로 설정.
- UFW를 활성화하고 부팅 시 자동 활성화 상태 확인.
- 서버 애플리케이션 기준 경로를 `/opt/what_changes_postgresql`로 확정.
- 디렉터리를 소유자 `rock:rock`, 권한 `0750`으로 생성.
- 작업에 사용한 `/etc/sudoers.d/what_changes_postgresql-p01` 임시 규칙 삭제.

최종 검증:

```text
UFW: active, enabled
Default incoming: deny
Default outgoing: allow
허용 수신: OpenSSH 22/tcp (IPv4, IPv6)
새 SSH 세션: 성공
PostgreSQL 공식 문서 HTTPS: HTTP 200
Chrony: Leap status Normal
외부 리슨 포트: 22/tcp만 존재
Application path: /opt/what_changes_postgresql
Owner/Mode: rock:rock / 0750
임시 sudoers: 삭제 완료
```

계획 대비 판정:

- Chrony 동기화, 업데이트 후 공개키 SSH 재접속, 승인된 외부 포트만 존재한다는 P01 완료 조건을 모두 충족함.
- P01 상태를 `완료`로 변경함.
- SSH 비밀번호 인증 비활성화는 서비스 접근 정책 확인 후 별도 보안 강화 작업으로 관리함.

### 2026-08-12 / P02 / Docker Engine과 Compose 설치

사전 고지:

- Ubuntu 26.04 공식 지원, 기존 충돌 패키지, 저장소 코드명과 서명 키를 먼저 확인한다고 알림.
- Docker 설치 스크립트 대신 공식 APT 저장소 방식을 사용한다고 알림.
- 설치 전 APT 시뮬레이션으로 추가·제거 패키지를 확인한다고 알림.

공식 저장소 검증:

- Docker 공식 문서에서 Ubuntu Resolute 26.04 LTS와 amd64 지원 확인.
- `https://download.docker.com/linux/ubuntu/dists/resolute/Release` HTTP 200 확인.
- Docker 기본 GPG 키 지문 `9DC858229FC7DD38854AE2D88D81803C0EBFCD88` 확인.
- 기존 Docker, containerd, runc 패키지가 없어 충돌 제거 작업은 수행하지 않음.
- Deb822 저장소를 `resolute`, `stable`, `amd64`로 제한해 등록.

설치 결과:

```text
Docker Engine/CLI: 29.7.2
containerd:         2.3.3
Docker Buildx:      0.36.1
Docker Compose:     5.4.0
신규 패키지:       7개
제거 패키지:       0개
추가 디스크:       약 395MB
docker/containerd: active, enabled
미설정 패키지:     0개
```

운영 설정:

- `/etc/docker/daemon.json`에 기본 로그 드라이버 `json-file` 적용.
- 컨테이너 로그를 파일당 `10MB`, 최대 `3개`로 제한.
- Docker 데몬 재시작 중 컨테이너를 유지하는 `live-restore` 활성화.
- `rock`을 `docker` 그룹에 추가하고 새 SSH 세션에서 sudo 없는 Docker API 접근 확인.
- Docker 그룹이 사실상 root 수준 권한임을 사용자에게 사전 고지함.
- 설정 원본을 `ops/docker/daemon.json`에 보관.

실행 검증:

- 공식 `hello-world` 컨테이너가 정상 종료 코드로 실행됨.
- 컨테이너 inspect에서 로그 설정 `max-size=10m`, `max-file=3` 상속 확인.
- Docker 데몬 재시작 전후 컨테이너 ID와 시작 시각이 같아 `live-restore` 작동 확인.

Compose 기반 검증:

- `ops/compose/runtime-check.compose.yaml` 검증 스택 작성.
- 내부 전용 네트워크, 명명 볼륨, healthcheck, `unless-stopped` 적용.
- CPU `0.25`, 메모리 `64MB`, PID `64`, 읽기 전용 루트, capability 전체 제거, `no-new-privileges` 적용 확인.
- 외부 공개 포트가 없는 상태에서 `healthy` 확인.
- 운영용 `compose.yaml`에 `edge`, 내부 `backend`, `postgres_data`, `source_snapshots`, `generated_reports` 이름을 정의.
- 운영 서비스가 아직 없으므로 Compose CLI가 미사용 네트워크와 볼륨을 런타임 구성에서 생략함. P04에서 서비스 연결 시 실제 생성 및 재검증함.

VM 재부팅 검증:

```text
이전 boot ID: c51cfa62-b544-4de4-ace6-ebd33b49751c
새 boot ID:   171bfb45-baa6-4c11-be94-d9f3b870a69e
Docker:       active, enabled
containerd:   active, enabled
UFW/SSH:      active
컨테이너:     running, healthy
재시작 정책:  unless-stopped
외부 포트:    없음
내부 network: true
first-started: 2026-08-12T09:00:30Z (보존)
last-started:  2026-08-12T09:01:50Z (갱신)
```

정리와 판정:

- 검증 후 테스트 컨테이너, 전용 네트워크와 전용 볼륨만 제거함.
- 검증용 Compose 파일과 이미지는 재시험을 위해 유지함.
- P02 작업용 임시 sudo 규칙 삭제 완료.
- P02 컨테이너 실행 기반 완료 조건을 충족함.
- 실제 운영 서비스의 자동 복구와 데이터 유지는 P04 구성 후, P10 출시 전 검증에서 다시 확인함.

### 2026-08-12 / P03 / Ollama 시험 준비

사전 고지:

- 운영 설치와 분리하여 사용자 홈에 벤치마크용 Ollama를 설치한다고 알림.

수행:

- 공식 Linux amd64 Ollama 패키지를 사용자 홈의 `~/opt/ollama-benchmark`에 설치.
- 버전 `0.32.9` 확인.
- systemd 사용자 임시 서비스 `ollama-benchmark.service`로 `127.0.0.1:11434` 실행.
- API 버전 응답 확인.
- Mac에 보유한 `ornith:9b` 모델을 LAN으로 복사 시작.

차이와 조치:

- VM 네트워크 전송속도가 낮아 모델 복사가 오래 걸림.
- 작업 기준 문서를 먼저 만들자는 사용자 요청에 따라 약 19%에서 복사를 중단.
- 복사 완료나 모델 성능 결론으로 기록하지 않음.

다음 시험:

1. 강화 프롬프트로 짧은 항목 사실성 재시험.
2. 중간/긴 변경 항목 실행.
3. JSON 유효성, 사실성, 처리시간, 토큰속도, 메모리 기록.
4. 20건 연속 안정성 시험.
5. 채택/제한/탈락 결정.

### 2026-08-12 / P03 / 모델 전송 검증과 짧은 항목 1차 시험

사전 고지:

- Mac과 VM의 파일 수, 용량, blob SHA-256과 Ollama 모델 인식을 확인한다고 알림.
- 이후 짧은 PostgreSQL 변경 항목 하나로 최초 로딩과 JSON 출력을 시험한다고 알림.

전송 검증:

- Mac 원본과 VM 대상에 blob 5개와 manifest 1개 존재.
- blob 5개의 SHA-256이 모두 일치.
- VM Ollama가 `ornith:9b`, 5.6GB 모델로 인식.

시험 입력:

```text
Add support for MERGE SQL command.
```

실측 결과:

```text
wall time: 18.576초
model load: 5.626초
prompt tokens: 126
output tokens: 42
generation speed: 5.799 tokens/second
model memory: 약 5.9GB
available system memory after load: 8.9GiB
swap used: 0B
JSON parse: 성공
```

품질 결과:

- 요약 필드와 JSON 구조는 정상.
- 원문에는 MERGE 명령 지원 추가만 있었으나, `customer_impact`에 여러 테이블 데이터 관리 설명을 생성함.
- 일반 지식으로는 타당할 수 있으나 입력 원문으로 직접 뒷받침되지 않으므로 계획서의 사실성 기준에는 실패.

판정:

- 짧은 항목 속도 기준은 최초 로딩 포함 20초 이내로 통과.
- 메모리 기준은 가용 4GB 이상으로 통과.
- JSON 유효성 통과.
- 사실성 기준 실패.
- 모델 채택 판정은 보류하고 더 엄격한 프롬프트와 후처리 규칙으로 재시험.

### 2026-08-12 / P03 / 정식 Ollama Docker 서비스 준비

사전 고지:

- 기존 임시 서비스와 모델 상태, 공식 Docker 배포 지원을 먼저 확인한다고 알림.
- 프롬프트 시험 전에 정식 실행 기반부터 구성하며, 이 단계에서는 모델을 메모리에 로딩하지 않는다고 알림.
- 기존 native 설치는 Docker 방식 검증 전까지 롤백용으로 보존한다고 알림.

방식 결정:

- 재부팅 후 임시 `ollama-benchmark.service`는 존재하지 않았고 실행 프로세스도 없었음.
- 기존 모델 5.3GB와 `ornith:9b` manifest는 정상 보존됨.
- 공식 Ollama 문서에서 CPU-only Docker 방식을 확인.
- OmniRoute와 동일한 내부 Docker 네트워크에서 호스트 포트 없이 연결할 수 있어 정식 실행 방식은 Docker로 결정.
- `ollama/ollama:0.32.9`의 Linux amd64 manifest 존재 확인.

모델 경로 정리:

- 모델 디렉터리를 `/home/rock/.ollama-benchmark/models`에서 `/opt/what_changes_postgresql/data/ollama/models`로 이동.
- 같은 파일시스템의 디렉터리 이동이며 대표 blob inode `2051:393303`이 전후 동일해 데이터 재복사가 없음을 확인.
- 이동 후 용량 5.3GB와 `ornith/9b` manifest 확인.
- 실제 모델 데이터와 서버 `.env`는 Git 추적 대상에서 제외.

Docker 구성:

- 이미지 `ollama/ollama:0.32.9` 사용.
- image ID와 RepoDigest `sha256:1685741456770df6e3cceb2a945a5f75e020f658d1701509668d6f4688f1dd3f` 확인.
- Compose 이미지 참조를 위 RepoDigest로 고정하고 재생성 후 실제 container image ID 일치 확인.
- 다운로드 레이어 약 2.52GB, 로컬 표시 이미지 크기 약 6.28GB.
- 호스트 포트를 publish하지 않고 내부 `what_changes_postgresql_backend` 네트워크에서만 `11434/tcp` expose.
- CPU 3개, 메모리 10GB, PID 512, 동시 모델 1개, 병렬 요청 1개로 제한.
- `unless-stopped`, 2분 종료 유예, healthcheck, 로그 `10MB x 3개` 적용.
- capability 전체 제거와 `no-new-privileges` 적용.
- `OLLAMA_NO_CLOUD=true`로 Ollama Cloud 조회와 Cloud 키 생성을 비활성화.

무추론 검증:

```text
Ollama version: 0.32.9
Container: running, healthy
Model: ornith:9b
Model digest: a75697c145891910e312c95e4a9fc1ccb8653e5ef543b23b0403a4665b82fd91
Model format: GGUF
Parameters: 9.0B
Quantization: Q4_K_M
Cloud: disabled
Host published ports: 없음
Internal endpoint: http://ollama:11434
Internal /api/tags: 성공
Loaded models: 0
Container restart: healthy 복귀, 같은 container ID 유지
Error/Panic/Fatal logs: 없음
Idle available memory: 약 14GiB
Swap used: 0B
Disk available: 70GB
```

판정과 남은 일:

- 정식 Ollama 실행 기반과 OmniRoute용 내부 접근 경로 준비 완료.
- 기존 native 설치 약 2.1GB는 강화 벤치마크 완료 전까지 롤백용으로 유지.
- 이 단계에서는 프롬프트나 모델 메모리 로딩을 수행하지 않음.
- P03 완료를 위해 강화 프롬프트의 짧은 항목, 중간/긴 항목, JSON·사실성, 연속 20건 시험과 최종 채택/제한/탈락 판정이 남음.

### 2026-08-12 / P03 / 전용 모델과 강화 짧은 시험 후 작업 중지

사전 고지:

- 설치 순서를 완료한 뒤에만 프롬프트 시험을 시작한다고 알림.
- 원본 `ornith:9b`는 변경하지 않고 PostgreSQL 요약 전용 파생 모델을 만든다고 알림.
- JSON Schema, `think=false`, temperature 0, 공식 PostgreSQL 원문으로 시험한다고 알림.
- 짧은 항목 결과를 확인하기 전에는 중간/긴 항목으로 넘어가지 않는다고 알림.

추가 구성:

- `ai/ollama/Modelfile`에 원문 한정, exact evidence, 불명확 영향 `unknown`, 빈 배열 사용 규칙 정의.
- `benchmarks/ollama/schema.json`에 고객용 요약 결과의 JSON Schema 정의.
- 공식 PostgreSQL 릴리스 노트 기반 짧은 167자, 중간 286자, 긴 896자 시험 원문 구성.
- Python 표준 라이브러리만 사용하는 `benchmarks/ollama/run.py` 작성.
- 실행기가 JSON parse, 필수 키, 타입, source ID, evidence의 원문 exact substring 포함 여부를 자동 검사하도록 구성.

비root 전환과 오류 처리:

- root 컨테이너에서 capability를 모두 제거한 상태로 파생 모델 생성 시 blob `chtimes` 권한 오류 발생.
- 데이터 용량 증가 0, 파생 manifest 미생성 확인 후 임의 capability 추가 대신 컨테이너를 UID/GID `1000:1000`으로 전환.
- 최초 비root 전환은 모델 mount가 `/root/.ollama/models`여서 `/root` 경로 통과 권한 오류로 재시작 루프 발생.
- 내부 mount를 `/models`, `OLLAMA_MODELS=/models`, `HOME=/tmp`로 변경해 복구.
- 최종 컨테이너는 UID/GID `1000:1000`, capability 전체 제거, `healthy`, 외부 publish 포트 없음.
- 이미지 내부 사용자명은 `ubuntu`지만 숫자 UID/GID가 호스트 `rock` 소유 모델 파일과 일치함.

파일 동기화 오류와 복구:

- 최초 `rsync` 대상 지정 오류로 `ai/`와 `benchmarks/` 파일이 서버의 `/opt/what_changes_postgresql/ollama`에 합쳐짐.
- 오배치 디렉터리에 이번 전송 파일만 존재함을 확인한 뒤 정확한 상대 경로로 재전송하고 오배치 디렉터리만 삭제.
- 모델 데이터 경로 `/opt/what_changes_postgresql/data/ollama/models` 5.3GB와 원본 manifest가 유지됨을 재검증.
- tmpfs `/tmp`로 `docker compose cp`가 성공 메시지를 출력해도 파일이 남지 않는 동작을 확인.
- 일회성 비root Ollama CLI 컨테이너에 Modelfile을 read-only bind mount하는 방식으로 전환.

전용 파생 모델 결과:

```text
Model: ornith-pg-brief:9b
Model ID: c29efbd00a98
Base model: ornith:9b
저장 증가량: 2,080 bytes
temperature: 0
top_k: 10
top_p: 0.8
num_ctx: 4096
num_predict: 768 (첫 시험 시점)
```

- 기존 5.6GB blob을 재사용하고 SYSTEM/파라미터 layer와 manifest만 추가됨.
- 생성 직후 모델이 메모리에 로딩되지 않은 상태 확인.

강화 짧은 시험:

- 입력: PostgreSQL 18 `uuidv7()`/`uuidv4()` 공식 릴리스 노트 발췌 167자.
- JSON Schema를 API `format`에 전달하고 `think=false`, temperature 0, seed 42로 실행.
- 결과 파일: 서버 `/opt/what_changes_postgresql/data/benchmarks/short-v2.json`.

```text
JSON Schema/parse: 통과
source_id: 통과
evidence exact substring 3개: 통과
원문 밖 고객 영향/조치: 생성하지 않음
customer impact: unknown / 빈 설명
사실성: 통과
wall time: 138.000초
model load: 17.858초
prompt: 545 tokens / 46.845초
output: 248 tokens / 73.260초
generation speed: 약 3.39 tokens/second
peak observed CPU: 약 445%
peak observed container memory: 약 5.8GiB
OOM: 없음
```

판정:

- 1차 단순 시험에서 실패했던 사실성은 강화 규칙과 Schema로 통과함.
- 짧은 항목 20초 목표는 크게 실패함.
- Schema를 프롬프트 본문과 API `format`에 중복 전달해 prompt가 545 token으로 커진 점이 주요 최적화 대상.
- 이 결과로 중간/긴 시험을 즉시 실행하지 않고 짧은 시험 최적화를 먼저 진행하기로 함.

중지 시점의 로컬 미배포 변경:

- `schema.json`: 문자열 길이와 배열 항목 수 제한 추가.
- `run.py`: 프롬프트 본문의 Schema 중복 제거, `num_predict` 768에서 384로 축소.
- `Modelfile`: 기본 `num_predict` 768에서 384로 축소.
- 위 세 최적화 파일은 로컬에만 작성됐고 서버 파일 및 파생 모델에는 아직 반영하지 않음.

중지 상태:

```text
Ollama container: healthy
Host published ports: 없음
ornith-pg-brief:9b: 디스크에 보존
Loaded models: 0 (수동 unload 완료)
Available memory: 약 14GiB
Swap: 사실상 0
Server result file: 보존
```

다음 재개 순서:

1. 로컬 Python/JSON/diff 검증 재실행.
2. 최적화된 `Modelfile`, `schema.json`, `run.py`만 정확한 상대 경로로 서버에 동기화.
3. `ornith-pg-brief:9b`를 새 Modelfile로 재생성하고 `num_predict=384` 확인.
4. 동일한 짧은 원문을 `short-v3.json`으로 1회 재시험.
5. 사실성·JSON 통과와 처리시간 개선 폭을 `short-v2.json`과 비교.
6. 속도가 수용 가능할 때만 중간/긴 항목 시험 진행. 여전히 과도하면 로컬 모델을 백그라운드/짧은 항목 제한으로 판정하고 Google fallback 설계로 이동.

### 2026-08-13 / P03 / 짧은 v3 시험과 AI 작업 후순위 전환

수행:

- Schema의 문자열 길이와 배열 개수를 제한하고 프롬프트 본문의 중복 Schema를 제거.
- 전용 모델과 실행기의 `num_predict`를 384로 축소.
- 동일한 `pg18-uuidv7-short` 원문으로 v3 시험 1회 수행.

비교 결과:

```text
항목                 v2          v3
wall time            138.00초    97.43초
model load            17.86초     9.29초
prompt tokens        545         287
prompt processing     46.85초    29.84초
output tokens        248         212
generation            73.26초    58.28초
JSON/evidence         통과        통과
```

판정:

- 약 29% 개선됐지만 짧은 항목 20초 기준은 여전히 크게 실패.
- `uuidv4()`가 evidence에는 포함됐지만 요약과 추가 항목에서 빠져 완전성도 충분하지 않음.
- 중간/긴 항목과 연속 20건 시험은 진행하지 않음.
- 모델을 unload했고 Ollama 컨테이너는 `healthy`, 호스트 공개 포트 없음, 가용 메모리 약 14GiB 상태.
- 사용자 지시에 따라 AI 요약과 OmniRoute를 마지막 단계로 이동.
- 다음 작업은 P04 애플리케이션·DB 골격, P05 공식 문서 수집, P06 버전 비교 엔진 순서로 진행.

### 2026-08-13 / P09 / 승인 보고서 출력과 파서 v2 정리

사전 고지:

- AI 요약은 마지막으로 유지하고 승인된 공식 원문 데이터의 출력 기능만 구현한다고 알림.
- DOCX와 PDF는 생성 성공만 확인하지 않고 실제 페이지로 렌더링해 한글과 레이아웃을 직접 검사한다고 알림.
- Docker 빌드·테스트·문서 생성은 Mac이 아닌 VM에서 수행.

구현:

- 로그인 사용자용 `/reports/export/` 출력 엔드포인트 추가.
- 고객용/DBA용 수준과 AS-IS/TO-BE 범위를 유지한 텍스트, Markdown, HTML, DOCX, PDF 출력.
- 승인된 `Review`만 포함하고, 승인자가 수정한 문구가 있으면 원문 대신 해당 문구를 출력.
- 승인 항목이 없으면 빈 문서를 만들지 않고 HTTP 400으로 거부.
- 모든 출력 항목에 PostgreSQL 공식 원문 링크 포함.
- 다운로드 파일명을 `postgresql-upgrade-<ASIS>-to-<TOBE>-<level>.<ext>` 형식으로 고정.
- DOCX/PDF에 Letter 용지, 1인치 여백, 제목 계층, 머리말·페이지 번호, NanumGothic 한글 글꼴 정책 적용.
- Docker 이미지에 `fonts-nanum`, Python에 `python-docx 1.2.0`, `reportlab 5.0.0` 추가.
- 비교 화면에 고객용/DBA용 텍스트·Markdown·HTML·DOCX·PDF 출력 링크 추가.

파서 v2 보정:

- PostgreSQL 릴리스 노트의 commit 링크 표시 문자 `§`만 구조화 텍스트에서 제거하고 원본 HTML은 보존.
- 기존 `ChangeItem` ID와 검수 이력을 유지하는 `upgrade_parser_v2_text` 관리 명령 추가.
- VM의 346개 현재 스냅샷을 parser v2로 갱신하고 15,521개 항목을 유지.
- 마이그레이션 후 섹션/항목 텍스트의 `§` 잔존 0건, rules-2 분류 15,521건 확인.

검증:

```text
Django tests: 28/28 통과
VM document sample: PostgreSQL 17.10 → 18.4, 승인 항목 6개
DOCX: 2페이지 렌더 및 전 페이지 육안 검수 통과
PDF: 2페이지 렌더 및 전 페이지 육안 검수 통과
한글 제목/본문/공식 링크: 정상
페이지 잘림/겹침: 없음
commit marker §: 없음
DOCX signature: PK
PDF signature: %PDF-
```

문서 검수 환경:

- 서버 생성물에 사용한 실제 NanumGothic TTF를 QA 렌더러의 fontconfig에 등록해 DOCX를 재현성 있게 렌더링.
- 첫 렌더에서 한글이 누락된 상태를 발견해 통과 처리하지 않고 글꼴 등록 문제를 수정한 뒤 재검수.
- PDF는 생성 시 NanumGothic을 내장해 별도 시스템 글꼴 없이 한글 렌더링 정상 확인.

계획 대비 남은 일:

- 실제 HTTPS 주소에서 클립보드 복사 동작 검증.
- Word 데스크톱에서 최종 DOCX 열기 확인은 출시 전 P11 사용자 환경 검증에 포함.
- 위 조건이 남아 있으므로 P09는 `완료`가 아니라 `진행`으로 유지.

### 2026-08-13 / P09 / 고객·프로젝트 보고서 프로필

구현:

- 관리자가 고객명, 프로젝트명, 선택 로고를 등록하는 `ReportProfile` 추가.
- 활성 프로필만 비교 화면에서 선택 가능하며 비활성·존재하지 않는 프로필 export는 HTTP 400으로 거부.
- 로고는 PNG/JPEG만 허용하고 2MB로 제한하며 SVG는 허용하지 않음.
- 프로필 metadata는 PostgreSQL, 로고 파일은 기존 백업 대상 `generated_reports/media`에 보관.
- 텍스트·Markdown·HTML·DOCX·PDF 다섯 출력에 동일한 고객명·프로젝트명을 적용.
- HTML은 로고를 data URI로 내장하고 DOCX/PDF는 원본 비율을 유지해 최대 영역 안에 배치.
- 비교 화면의 출력 링크와 페이지 이동에 검증된 프로필 ID를 유지.

검증:

```text
Migration: releases.0006_reportprofile 적용
Migration drift: 없음
Django tests: 31/31 통과
DOCX: 로고 포함 2페이지 렌더, 전체 페이지 육안 검수 통과
PDF: 로고 포함 2페이지 렌더, 전체 페이지 육안 검수 통과
DOCX/PDF 공식 원문 링크: 각각 6개
한글 고객명/프로젝트명: 정상
로고 비율/정렬: 정상
잘림/겹침/누락 glyph: 없음
기존 데이터: 346 / 346 / 15,521건 유지
QA 임시 프로필/승인: 0건으로 정리
```

판정:

- 계획의 고객명·프로젝트명·로고 결합 조건 완료.
- 실제 HTTPS 클립보드와 Word 데스크톱 확인이 남아 P09는 `진행` 유지.

### 2026-08-13 / P10 / 백업·복원 검증과 상태 감시 기반

구현:

- PostgreSQL custom dump, 원문 스냅샷 tar, 생성 보고서 tar를 한 세트로 백업.
- 각 세트에 SHA-256 체크섬과 생성시각·호스트·배포/이미지 ID metadata 기록.
- 임시 디렉터리에 완성한 뒤 timestamp 디렉터리로 이동하고 기본 35일 보존.
- VM 루트와 `tmpfs`, `devtmpfs`, `overlay`, `squashfs`는 외부 백업 경로로 인정하지 않고 실패.
- 운영 DB를 덮지 않는 임시 검증 DB 복원 명령 구현.
- 운영과 이름이 겹치지 않는 별도 Compose 프로젝트에 DB·원문·생성 문서 볼륨을 모두 복원하는 전체 드릴 구현.
- 수집·지원정보·파싱·분류 4단계를 하나의 flock 구간으로 묶어 백업과 동시 실행되지 않도록 보완.
- 디스크 70%와 `db`/`web` container health를 검사하는 hourly systemd unit 추가.
- `docs/OPERATIONS.md`에 외부 저장소 준비, timer 설치, 검증, 장애 확인 절차 기록.

실제 VM 드릴:

```text
외부경로 강제: /tmp(tmpfs) 거부, exit 3 통과
드릴 백업 크기: 8.0MB
파일 권한: 모두 0600
SHA-256: database/source snapshots/generated reports/metadata 모두 OK
tar 무결성: 2종 통과
임시 DB 복원: 성공
복원 릴리스: 346건
복원 원문 스냅샷: 346건
복원 변경항목: 15,521건
임시 검증 DB: 시험 후 제거
드릴 백업: 시험 후 /tmp에서 제거
현재 디스크: 25%, 70% 기준 정상
강제 1% 기준: CRITICAL 및 exit 1 통과
db/web: running, healthy
systemd-analyze verify: 통과
systemd 설치: sync timer 및 health timer enabled/active
health oneshot: Result=success, ExecMainStatus=0
격리 전체 복원 DB: 346 / 346 / 15,521건
격리 전체 복원 원문 파일: 347개(릴리스 346 + 지원정보 1)
격리 전체 복원 생성 문서: 0개(운영 원본과 동일)
복원 웹: healthy, database up
복원 웹 outbound network 차단: 성공
외부망 차단 후 9.2.10 → 18.4 비교: 13,110건
드릴 컨테이너/볼륨/네트워크/백업: 시험 후 제거
```

남은 조건:

- 실제 NFS/NAS/별도 디스크 경로가 정해질 때까지 backup timer는 의도적으로 활성화하지 않음.
- 외부 알림 채널, 실제 외부 저장소와 물리적으로 다른 VM 복구 시험이 남아 있으므로 P10은 `진행` 유지.

### 2026-08-13 / P10 / VM 재부팅 자동복구 검증

```text
Boot time: 2026-08-13 13:57:46 KST
Docker: active
db: running, healthy
web: running, healthy
sync timer: enabled, active
health timer: enabled, active
재부팅 후 health service: Result=success, ExecMainStatus=0
웹 health: status healthy, database up
데이터: 346 releases / 346 current snapshots / 15,521 change items
```

- VM 재부팅 후 서비스·timer·데이터 자동복구 완료조건 통과.
- 실제 외부 백업 저장소와 외부 경고 전달 채널은 아직 미정이므로 P10은 `진행` 유지.

## 4. AI 라우팅 결정 기록

현재 확정 순서:

```text
Ollama ornith:9b
→ Google
→ Grok(xAI)
→ Mistral
```

아직 확정되지 않은 사항:

- 공급자별 구체 모델명
- 무료 API의 현재 한도와 상업적 이용조건
- timeout 값
- 일/월 요청 예산
- 오류 종류별 fallback 조건

이 항목들은 실제 API 연결 시험 후 기록한다.
