# Installation & Setup Guide ⚙️

Simple Order Management Platform의 설치 및 설정 가이드입니다.

## 📋 시스템 요구사항

### 기본 요구사항
- **Python**: 3.9 이상
- **Operating System**: Linux, macOS, Windows (WSL 권장)
- **RAM**: 최소 4GB, 권장 8GB
- **Storage**: 1GB 여유 공간

### IBKR 요구사항
- **IB Gateway** 또는 **TWS (Trader Workstation)** 실행 중
- **API 접근 권한**: IB 계정에서 API 활성화 필요
- **관리 계좌 권한**: 여러 계좌 관리 시 필요

## 🚀 설치 방법

### Method 1: Git Clone (권장)

```bash
# 1. 리포지토리 클론
git clone https://github.com/my2582/simple-order-management-platform.git
cd simple-order-management-platform

# 2. 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는 Windows에서:
# venv\Scripts\activate

# 3. 패키지 설치 (개발 모드)
pip install -e .

# 4. 설치 확인
simple-order --help
```

### Method 2: 직접 설치

```bash
# 1. 의존성 설치
pip install ib-insync>=0.9.86 pandas>=2.0.0 openpyxl>=3.1.0 pydantic>=2.0.0 typer[all]>=0.9.0 rich>=13.0.0 tenacity>=8.2.0 pyarrow>=19.0.0

# 2. 소스 코드 다운로드 후 설치
pip install -e /path/to/simple-order-management-platform
```

### Method 3: pip 설치 (향후 제공 예정)

```bash
# PyPI 배포 시 사용 가능
pip install simple-order-management-platform
```

## ⚙️ 설정

### 1. 기본 설정 파일

프로젝트 루트의 `config/app.yaml` 파일을 확인/수정하세요:

```yaml
# config/app.yaml
app:
  directories:
    output_dir: "./data/output"
    model_portfolio_dir: "./data/model_portfolios"
  
ibkr:
  connection:
    host: "127.0.0.1"
    port: 4002  # Paper Trading: 4002, Live Trading: 7497
    client_id: 1
  
  settings:
    timeout: 30
    retry_attempts: 3
    retry_delay: 1.0

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 2. 디렉토리 구조 확인

설치 후 다음 디렉토리 구조가 생성되어야 합니다:

```
simple-order-management-platform/
├── config/
│   └── app.yaml                  # 메인 설정 파일
├── data/
│   ├── model_portfolios/
│   │   └── MP_Master.csv         # 모델 포트폴리오 정의
│   └── output/                   # 출력 파일들 (자동 생성)
├── src/
│   └── simple_order_management_platform/
└── docs/
```

### 3. 모델 포트폴리오 설정

`data/model_portfolios/MP_Master.csv` 파일을 확인하세요:

```csv
Portfolio ID,Bucket Name,ISIN,Ticker,Weight,Effective Date
B301,Future Fund - GTAA,,SPMO,33.34,18/07/25
B301,Future Fund - GTAA,,SMH,33.33,18/07/25
B301,Future Fund - GTAA,,IAU,33.33,18/07/25
B101,Peace of Mind,,VTI,50.00,01/01/25
B101,Peace of Mind,,BND,50.00,01/01/25
```

## 🔗 IBKR 연결 설정

### 1. IB Gateway 설정

#### TWS/Gateway 다운로드
1. [Interactive Brokers 공식 사이트](https://www.interactivebrokers.com/en/trading/tws.php)에서 TWS 또는 Gateway 다운로드
2. 설치 후 실행

#### API 설정 활성화
1. **TWS**: File → Global Configuration → API → Settings
2. **Gateway**: Configure → Settings → API

필수 설정:
- ✅ **Enable ActiveX and Socket Clients** 체크
- ✅ **Allow connections from localhost only** 체크 (보안상 권장)
- ✅ **Read-Only API** 체크 해제 (주문 생성 시 필요)
- **Socket port**: 4002 (Paper Trading) 또는 7497 (Live Trading)

#### 신뢰할 수 있는 IP 설정 (선택사항)
보안 강화를 위해 특정 IP만 허용:
1. API Settings에서 **Trusted IPs** 설정
2. 로컬 개발: `127.0.0.1` 추가
3. 원격 서버: 해당 서버 IP 추가

### 2. 계정 권한 설정

#### 단일 계좌 사용
- 별도 설정 불필요
- 로그인한 계좌로 자동 접근

#### 여러 계좌 관리
1. **Account Management**에서 **Account Permissions** 설정
2. **Managed Accounts** 권한 부여
3. API로 접근할 계좌들을 명시적으로 허용

### 3. 연결 테스트

설정 완료 후 연결을 테스트하세요:

```bash
# 기본 연결 테스트
simple-order test-connection

# 다른 포트로 테스트 (Live Trading)
simple-order test-connection --ib-port 7497

# 원격 Gateway 테스트
simple-order test-connection --ib-host 192.168.1.100 --ib-port 4002
```

성공 시 출력 예시:
```
✅ IB Connection Test Successful
📊 Connected to IB Gateway
🏢 Account: DU123456
💰 Net Liquidation: $100,000.00
⏰ Server Time: 2025-09-06 09:30:00 EST
```

## 🛠️ 고급 설정

### 1. 환경 변수 설정 (선택사항)

민감한 정보를 환경 변수로 관리:

```bash
# .env 파일 생성
cat > .env << EOF
IB_HOST=127.0.0.1
IB_PORT=4002
IB_CLIENT_ID=1
OUTPUT_DIR=./data/output
EOF

# 환경 변수 로드
export $(cat .env | xargs)
```

### 2. 로깅 설정

더 상세한 로깅이 필요한 경우 `config/app.yaml` 수정:

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/app.log"  # 파일 로깅 (선택사항)
```

### 3. 성능 튜닝

대용량 계좌나 포지션 처리 시:

```yaml
ibkr:
  settings:
    timeout: 60        # 연결 타임아웃 증가
    retry_attempts: 5  # 재시도 횟수 증가
    retry_delay: 2.0   # 재시도 간격 증가
    
  performance:
    batch_size: 50     # 배치 처리 크기
    rate_limit: 0.1    # API 호출 간격 (초)
```

## ✅ 설치 검증

### 1. 기본 기능 테스트

```bash
# 1. 명령어 확인
simple-order --help

# 2. 연결 테스트
simple-order test-connection

# 3. 포트폴리오 목록 확인
simple-order list-portfolios

# 4. 샘플 데이터 다운로드 시도
simple-order download-positions --accounts DU123456 --output test.xlsx
```

### 2. 종속성 확인

```bash
# Python 패키지 확인
pip list | grep -E "(ib-insync|pandas|openpyxl|pydantic|typer|rich)"

# 버전 확인
python -c "import ib_insync; print(f'ib-insync: {ib_insync.__version__}')"
```

### 3. 파일 시스템 권한 확인

```bash
# 출력 디렉토리 쓰기 권한 확인
mkdir -p data/output
touch data/output/test_file.txt
rm data/output/test_file.txt

# 설정 파일 읽기 권한 확인
cat config/app.yaml
```

## 🚨 문제 해결

### 일반적인 설치 문제

**1. Python 버전 호환성**
```bash
# Python 버전 확인
python --version
# 3.9 미만인 경우 업그레이드 필요
```

**2. 패키지 설치 실패**
```bash
# pip 업그레이드
pip install --upgrade pip

# 개별 패키지 설치 시도
pip install ib-insync pandas openpyxl pydantic typer rich tenacity pyarrow
```

**3. 권한 문제 (Linux/Mac)**
```bash
# 사용자 권한으로 설치
pip install --user -e .

# 또는 sudo 사용 (권장하지 않음)
sudo pip install -e .
```

**4. Windows 설치 문제**
```bash
# Microsoft Visual C++ Build Tools 필요할 수 있음
# 또는 conda 사용
conda install -c conda-forge ib-insync pandas openpyxl pydantic
pip install typer rich tenacity pyarrow
```

### IBKR 연결 문제

**1. 연결 거부**
```
ConnectionRefusedError: [Errno 61] Connection refused
```
- IB Gateway/TWS가 실행 중인지 확인
- 포트 번호 확인 (4002 vs 7497)
- 방화벽 설정 확인

**2. API 비활성화**
```
Error: API not enabled
```
- TWS/Gateway에서 API 설정 활성화
- Socket Clients 허용 설정 확인

**3. 로그인 문제**
```
Error: Not logged in
```
- TWS/Gateway에 로그인되어 있는지 확인
- 계정 상태 확인

### 성능 문제

**1. 느린 데이터 다운로드**
- `config/app.yaml`에서 timeout 값 증가
- 배치 크기 조정
- 네트워크 연결 상태 확인

**2. 메모리 부족**
- 대용량 데이터 처리 시 계좌를 나누어 처리
- Python 메모리 할당량 확인

## 🔄 업그레이드

### 패키지 업그레이드

```bash
# Git pull로 최신 버전 받기
git pull origin main

# 의존성 업데이트
pip install --upgrade -e .

# 또는 requirements.txt 사용
pip install --upgrade -r requirements.txt
```

### 설정 파일 마이그레이션

새 버전으로 업그레이드 시 설정 파일 백업:

```bash
# 백업 생성
cp config/app.yaml config/app.yaml.backup

# 새 설정 파일과 비교
diff config/app.yaml.backup config/app.yaml
```

## 📞 지원

설치나 설정 관련 문제가 있으면:

1. **GitHub Issues**: 버그 리포트나 기능 요청
2. **Documentation**: 이 문서와 다른 가이드들 참조
3. **로그 확인**: 상세한 오류 메시지 확인

성공적인 설치를 위해 이 가이드를 단계별로 따라하세요!