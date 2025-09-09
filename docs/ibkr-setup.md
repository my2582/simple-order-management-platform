# IBKR Connection Setup Guide 🔗

Interactive Brokers와의 연결 설정에 대한 상세 가이드입니다.

## 📋 IBKR 개요

### TWS vs IB Gateway

| 구분 | TWS (Trader Workstation) | IB Gateway |
|------|-------------------------|------------|
| **용도** | 완전한 거래 플랫폼 | API 연결 전용 |
| **GUI** | 풀 기능 인터페이스 | 최소한의 인터페이스 |
| **리소스** | 높은 메모리/CPU 사용 | 낮은 리소스 사용 |
| **권장 사용** | 수동 거래 + API | API 전용 서버 |

**권장**: API만 사용하는 경우 **IB Gateway** 사용

### Paper Trading vs Live Trading

| 구분 | Paper Trading | Live Trading |
|------|---------------|--------------|
| **포트** | 4002 | 7497 |
| **용도** | 테스트 환경 | 실제 거래 |
| **자금** | 가상 자금 | 실제 자금 |
| **데이터** | 실시간 시장 데이터 | 실시간 시장 데이터 |

**권장**: 개발 및 테스트는 **Paper Trading**부터 시작

## 🚀 단계별 설정

### 1단계: IB Gateway 다운로드 및 설치

#### 다운로드
1. [Interactive Brokers 다운로드 페이지](https://www.interactivebrokers.com/en/trading/tws.php) 방문
2. **IB Gateway** 선택 (더 가벼움)
3. 운영 체제에 맞는 버전 다운로드

#### 설치
```bash
# Linux 설치 예시
chmod +x ibgateway-latest-linux-x64.sh
./ibgateway-latest-linux-x64.sh

# macOS 설치
# .dmg 파일 다운로드 후 일반적인 앱 설치 과정

# Windows 설치
# .exe 파일 실행 후 설치 마법사 따라하기
```

### 2단계: 계정 준비

#### Paper Trading 계정 생성
1. [IB 웹사이트](https://www.interactivebrokers.com/en/home.php)에서 계정 생성
2. **Paper Trading Account** 신청
3. 승인 후 로그인 정보 확인

#### Live Trading 계정 (실거래)
1. 실제 자금으로 계정 개설
2. 최소 잔고 요구사항 충족
3. API 거래 권한 신청

### 3단계: IB Gateway 실행 및 로그인

#### IB Gateway 시작
```bash
# Linux/Mac에서 백그라운드 실행
nohup /opt/ibc/twsstart.sh &

# 또는 GUI 환경에서 직접 실행
```

#### 로그인 정보 입력
- **Username**: IB 계정 사용자명
- **Password**: IB 계정 비밀번호
- **Trading Mode**: 
  - Paper Trading (테스트)
  - Live Trading (실거래)

### 4단계: API 설정 구성

#### API Settings 접근
1. IB Gateway 실행 후 **Configure** 클릭
2. **Settings** → **API** 선택

#### 필수 설정 항목

##### ✅ 기본 API 설정
```
☑️ Enable ActiveX and Socket Clients
☑️ Allow connections from localhost only (보안상 권장)
☐ Read-Only API (주문 기능 사용 시 해제)
```

##### 🔌 포트 설정
```
Socket port: 4002 (Paper Trading)
Socket port: 7497 (Live Trading)
```

##### 🛡️ 보안 설정
```
☑️ Allow connections from localhost only
Client ID: 1 (기본값, 필요 시 변경)
```

##### ⏰ 타임아웃 설정
```
API idle timeout: 자동 (또는 더 긴 시간 설정)
```

### 5단계: 고급 설정

#### Trusted IP 설정 (권장)
특정 IP에서만 API 접근 허용:

1. **API Settings**에서 **Trusted IPs** 체크
2. 허용할 IP 주소 추가:
   - `127.0.0.1` (로컬 개발)
   - 서버 IP (원격 배포 시)

#### 로깅 설정
API 호출 로깅 활성화:
```
☑️ Create API message log file
Log Level: Detail (개발 시), Error (운영 시)
```

#### 자동 재시작 설정
연결 안정성을 위한 설정:
```
☑️ Auto restart
Restart time: 23:45 (거래 시간 외)
```

## ⚙️ 연결 테스트

### 1. 기본 연결 확인

```bash
# Simple Order 플랫폼으로 테스트
simple-order test-connection

# 성공 시 출력 예시:
# ✅ IB Connection Test Successful
# 📊 Connected to IB Gateway  
# 🏢 Account: DU123456
# 💰 Net Liquidation: $1,000,000.00
# ⏰ Server Time: 2025-09-06 09:30:00 EST
```

### 2. 포트별 테스트

```bash
# Paper Trading 포트 (4002)
simple-order test-connection --ib-port 4002

# Live Trading 포트 (7497)
simple-order test-connection --ib-port 7497

# 커스텀 설정
simple-order test-connection --ib-host 192.168.1.100 --ib-port 4002 --ib-client-id 2
```

### 3. 계정 정보 확인

```bash
# 계정 포지션 다운로드 테스트
simple-order positions --accounts DU123456 --output test.xlsx
```

## 🔧 계정별 상세 설정

### 단일 계좌 설정
가장 간단한 설정으로, 로그인한 계좌로만 작업:

```yaml
# config/app.yaml
ibkr:
  connection:
    host: "127.0.0.1"
    port: 4002
    client_id: 1
```

### 다중 계좌 관리 설정

#### 1. IB에서 권한 설정
1. **Account Management** 로그인
2. **Users and Access** → **API** 
3. 관리할 계좌들을 **Managed Accounts**에 추가

#### 2. 플랫폼 설정
```yaml
# config/app.yaml
ibkr:
  connection:
    host: "127.0.0.1"  
    port: 4002
    client_id: 1
  
  accounts:
    managed_accounts:
      - "DU123456"  # 메인 계좌
      - "DU789012"  # 관리 계좌 1
      - "DU345678"  # 관리 계좌 2
```

#### 3. 권한 확인
```bash
# 모든 관리 계좌 확인
simple-order positions

# 특정 계좌만 확인  
simple-order positions --accounts "DU123456,DU789012"
```

## 🌐 원격 서버 설정

### 클라우드/VPS에서 IB Gateway 실행

#### 1. 헤드리스 환경 설정
GUI 없는 환경에서 IB Gateway 실행:

```bash
# VNC 서버 설치 (Ubuntu 예시)
sudo apt update
sudo apt install tightvncserver

# VNC 시작
vncserver :1 -geometry 1024x768 -depth 24

# IB Gateway를 VNC 세션에서 실행
export DISPLAY=:1
/opt/ibgateway/ibgateway &
```

#### 2. IBC (IB Controller) 사용
자동화된 로그인을 위한 IBC 설정:

```bash
# IBC 다운로드 및 설치
wget https://github.com/IbcAlpha/IBC/releases/latest/download/IBCLinux.zip
unzip IBCLinux.zip -d /opt/ibc

# 설정 파일 편집
vim /opt/ibc/config.ini
```

**IBC 설정 예시**:
```ini
# config.ini
IbLoginId=your_username
IbPassword=your_password
TradingMode=paper  # 또는 live
IbDir=/opt/ibgateway
```

#### 3. 보안 설정
```bash
# 방화벽 설정 (포트 4002만 허용)
sudo ufw allow from YOUR_IP to any port 4002

# SSH 터널링 (더 안전함)
ssh -L 4002:localhost:4002 user@server_ip
```

### Docker 환경 설정

IB Gateway를 Docker로 실행:

```dockerfile
# Dockerfile
FROM ubuntu:20.04

# IB Gateway 설치
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    x11vnc

# IB Gateway 다운로드 및 설치
RUN wget -q https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-linux-x64.sh
RUN chmod +x ibgateway-latest-linux-x64.sh && ./ibgateway-latest-linux-x64.sh -q

# 시작 스크립트
COPY start-ibgateway.sh /start-ibgateway.sh
RUN chmod +x /start-ibgateway.sh

EXPOSE 4002
CMD ["/start-ibgateway.sh"]
```

## 🚨 문제 해결

### 연결 오류

#### 1. Connection Refused
```
ConnectionRefusedError: [Errno 61] Connection refused
```

**원인 및 해결**:
- ❌ IB Gateway가 실행되지 않음 → IB Gateway 시작
- ❌ 잘못된 포트 → 포트 확인 (4002 vs 7497)
- ❌ 방화벽 차단 → 방화벽 설정 확인

#### 2. Authentication Failed
```
Error: Authentication failed
```

**원인 및 해결**:
- ❌ 잘못된 로그인 정보 → 계정 정보 확인
- ❌ 계정 잠금 → IB 고객센터 문의
- ❌ API 권한 없음 → 계정 설정에서 API 권한 활성화

#### 3. No Access to Account
```
Error: No access to account DU123456
```

**원인 및 해결**:
- ❌ 계좌 번호 오타 → 정확한 계좌 번호 확인
- ❌ 관리 권한 없음 → Account Management에서 권한 설정
- ❌ 계좌 상태 문제 → 계좌 상태 확인

### 데이터 수신 문제

#### 1. 시장 데이터 구독 오류
```
Error: No market data permissions
```

**해결책**:
1. IB 계정에서 시장 데이터 구독 확인
2. Paper Trading에서도 Live 데이터 구독 필요할 수 있음
3. 데이터 권한 신청

#### 2. 위치 정보 오류 (Position 0)
```
Warning: Position showing as 0 but market value exists
```

**해결책**:
1. TWS/Gateway에서 포지션 새로고침
2. 계좌 동기화 대기 (최대 몇 분)
3. 다른 Client ID로 재연결

### 성능 최적화

#### 1. 연결 안정성 향상
```yaml
# config/app.yaml
ibkr:
  settings:
    timeout: 60          # 연결 타임아웃 증가
    retry_attempts: 5    # 재시도 횟수 증가  
    retry_delay: 2.0     # 재시도 간격 증가
    keep_alive: true     # 연결 유지
```

#### 2. 데이터 수집 최적화
```yaml
ibkr:
  performance:
    batch_size: 20       # 배치 크기 조정
    rate_limit: 0.1      # API 호출 제한
    parallel_accounts: 3  # 병렬 계좌 처리
```

## 📊 모니터링 및 유지보수

### 연결 상태 모니터링

정기적인 연결 확인 스크립트:
```bash
#!/bin/bash
# monitor_ibkr.sh

while true; do
    if simple-order test-connection > /dev/null 2>&1; then
        echo "$(date): IB Gateway connection OK"
    else
        echo "$(date): IB Gateway connection FAILED"
        # 알림 또는 재시작 로직
    fi
    sleep 300  # 5분마다 확인
done
```

### 자동 재시작 설정

IB Gateway 자동 재시작 (cron):
```bash
# crontab -e
0 23 * * * /usr/bin/pkill -f ibgateway && sleep 60 && /opt/ibgateway/ibgateway &
```

### 로그 관리

API 로그 정기 정리:
```bash
# cleanup_logs.sh
find /home/user/Jts/ibgateway -name "*.log" -mtime +7 -delete
find ./logs -name "app.log.*" -mtime +30 -delete
```

이 가이드를 통해 안정적이고 안전한 IBKR 연결을 구성할 수 있습니다.