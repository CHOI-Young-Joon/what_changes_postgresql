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
| P00 | 문서 및 Git 기준선 | 진행 | Git 저장소 초기화와 원격 접근 확인, 계획서·작업기록·제외규칙 작성 | 최초 커밋과 push 전 | 문서 검증 후 커밋/push |
| P01 | VM 안정화 | 진행 | VM 자원, 네트워크, 업데이트, 시간 상태 점검 | Chrony 실행 중이나 동기화 실패 | NTP 경로 결정 및 수정 |
| P02 | 컨테이너 실행 기반 | 대기 | Docker 미설치 확인 | sudo 필요 | P01 완료 후 설치 |
| P03 | 로컬 Ollama 벤치마크 | 진행 | 사용자 홈에 Ollama 0.32.9 시험 바이너리 설치, localhost 시험 서비스 정상 | 모델 복사를 19%에서 중단. 기준 문서 작성이 선행되지 않았음 | 문서 기준 확정 후 모델 전송 재개 |
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

- 최초 문서 커밋.
- 사용자에게 변경사항과 검증 결과를 알린 뒤 push.

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

1. 모델 전송 재개 및 무결성 확인.
2. Ollama 모델 목록 확인.
3. 짧은/중간/긴 변경 항목 실행.
4. JSON 유효성, 사실성, 처리시간, 토큰속도, 메모리 기록.
5. 20건 연속 안정성 시험.
6. 채택/제한/탈락 결정.

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
