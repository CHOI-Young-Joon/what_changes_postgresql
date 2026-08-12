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
| P02 | 컨테이너 실행 기반 | 완료 | Docker Engine·Compose 설치, 전역 로그 제한·live-restore 적용, 내부 네트워크·볼륨·healthcheck·자원 제한·재부팅 자동 복구 실증 | 운영 서비스가 아직 없어 실제 운영 네트워크·볼륨은 P04에서 생성됨 | P03 정식 Ollama 준비 후 계획된 벤치마크 진행 |
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
