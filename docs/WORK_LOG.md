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
| P01 | VM 안정화 | 진행 | VM 자원·네트워크 점검, 외부 NTP 정상화, `Asia/Seoul` 적용, OS 전체 업데이트와 재부팅 후 SSH·시간·서비스 검증 완료 | 방화벽/공개 포트 정책과 서버 애플리케이션 디렉터리 확정 남음 | 현재 리슨 포트 점검 후 방화벽 정책 적용 |
| P02 | 컨테이너 실행 기반 | 대기 | Docker 미설치 확인 | sudo 필요 | P01 완료 후 설치 |
| P03 | 로컬 Ollama 벤치마크 | 진행 | `ornith:9b` 전송과 해시 검증 완료, Ollama 인식 확인, 짧은 항목 1차 시험 완료 | 속도·메모리는 기준 충족, 원문에 없는 고객 영향 추론으로 사실성 기준 미충족 | 강화 프롬프트 재시험 후 중간·긴 항목 시험 |
| P04 | 애플리케이션 골격 | 대기 | 미착수 | 없음 | P02 이후 진행 |
| P05 | 공식 문서 수집기 | 대기 | 미착수 | 없음 | P04 이후 진행 |
| P06 | 버전 비교 엔진 | 대기 | 미착수 | 없음 | P05 이후 진행 |
| P07 | AI 및 OmniRoute | 대기 | 라우팅 순서만 확정 | 공급자 API 키와 무료 한도 미확인 | P03 결과 후 연결 |
| P08 | 검수 및 고객 화면 | 대기 | 미착수 | 없음 | P07 이후 진행 |
| P09 | 출력 문서 | 대기 | 미착수 | 도메인/HTTPS 미정 | P08 이후 진행 |
| P10 | 운영과 복구 | 대기 | 미착수 | 외부 백업 위치 미정 | 배포 전 확정 |
| P11 | 시범 검증과 출시 | 대기 | 미착수 | 없음 | P00~P10 이후 진행 |

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
- 남음: 방화벽과 공개 포트 정책 적용, 서버 애플리케이션 디렉터리 확정.
- 따라서 P01 상태는 `진행`을 유지함.

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
