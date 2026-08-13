# PostgreSQL Upgrade Brief 운영 절차

## 1. 현재 운영 위치

- VM 프로젝트: `/opt/what_changes_postgresql`
- 운영 데이터: PostgreSQL, `source_snapshots`, `generated_reports` Docker volume
- 일일 수집: `what-changes-postgresql-sync.timer`
- 상태 감시: `what-changes-postgresql-health.timer`
- 외부 공개 포트: 없음

## 2. 외부 백업 저장소 준비

백업은 VM 루트 디스크와 `tmpfs`, `overlay`, `squashfs`를 기본적으로 거부한다. NFS, NAS 또는 별도 영구 디스크를 먼저 `/mnt/what-changes-backup` 등에 마운트한다.

```sh
sudo install -d -m 0750 -o rock -g rock /etc/what-changes-postgresql
sudo vi /etc/what-changes-postgresql/backup.env
```

설정 예:

```text
WHAT_CHANGES_BACKUP_ROOT=/mnt/what-changes-backup
WHAT_CHANGES_BACKUP_RETENTION_DAYS=35
WHAT_CHANGES_RELEASE_ID=<배포 커밋 또는 릴리스 ID>
```

백업 service와 timer 설치:

```sh
sudo install -m 0644 /opt/what_changes_postgresql/ops/systemd/what-changes-postgresql-backup.service /etc/systemd/system/what-changes-postgresql-backup.service && sudo install -m 0644 /opt/what_changes_postgresql/ops/systemd/what-changes-postgresql-backup.timer /etc/systemd/system/what-changes-postgresql-backup.timer && sudo systemctl daemon-reload && sudo systemctl enable --now what-changes-postgresql-backup.timer
```

첫 수동 실행과 결과 확인:

```sh
sudo systemctl start what-changes-postgresql-backup.service && sudo systemctl status --no-pager what-changes-postgresql-backup.service && sudo journalctl -u what-changes-postgresql-backup.service -n 100 --no-pager
```

## 3. 백업 내용과 검증

각 백업 디렉터리에는 다음 파일이 생성된다.

- `database.dump`: PostgreSQL custom format dump
- `source_snapshots.tar.gz`: 공식 원문 스냅샷
- `generated_reports.tar.gz`: 생성 보고서
- `metadata.txt`: 생성시각, 호스트, 배포 ID, 이미지 ID
- `SHA256SUMS`: 무결성 체크섬

운영 DB를 덮지 않고 임시 검증 DB에 복원하는 명령:

```sh
/opt/what_changes_postgresql/ops/backup/verify_restore.sh /mnt/what-changes-backup/what_changes_postgresql/<UTC_TIMESTAMP>
```

성공 시 체크섬과 tar 검증, 임시 DB 복원, 핵심 테이블 건수를 출력한 뒤 임시 DB를 제거한다.

## 4. 상태 감시

상태 감시는 매시간 루트 디스크와 `db`, `web` 컨테이너를 검사한다. 디스크 사용률 70% 이상 또는 컨테이너 비정상 시 service가 실패하고 journal에 `CRITICAL`을 기록한다.

```sh
systemctl list-timers what-changes-postgresql-health.timer --no-pager
sudo systemctl status --no-pager what-changes-postgresql-health.service
sudo journalctl -u what-changes-postgresql-health.service -n 100 --no-pager
```

외부 메일·Slack 알림은 아직 연결하지 않았다. systemd/journal 실패를 외부 모니터링에 연결하는 작업이 남아 있다.

## 5. 장애 확인

```sh
cd /opt/what_changes_postgresql && docker compose ps && docker compose logs --tail=100 web db
```

웹 상태 점검:

```sh
cd /opt/what_changes_postgresql && docker compose exec -T web python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/", timeout=5).read().decode())'
```

운영 DB나 volume을 삭제하는 전체 복구는 이 문서의 검증 명령과 다르다. 빈 VM 전체 복구 자동화와 실제 외부 백업 저장소 시험이 끝나기 전에는 P10을 완료 처리하지 않는다.
