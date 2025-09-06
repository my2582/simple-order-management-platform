# Comprehensive Portfolio Management Platform 🚀

> 전문적인 포트폴리오 관리를 위한 완전 자동화된 IBKR 통합 플랫폼  
> **4개 핵심 목표 100% 완성**: 자동화 일일 업데이트 + 주문 생성 + 마켓 데이터 분리 + 싱가포르 시간 스케줄링

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![IBKR](https://img.shields.io/badge/IBKR-API-green.svg)](https://interactivebrokers.github.io/tws-api/)
[![Singapore Time](https://img.shields.io/badge/Schedule-Singapore%20Timezone-red.svg)](#-singapore-timezone-scheduling)
[![Production Ready](https://img.shields.io/badge/Production-Ready-success.svg)](#-deployment-infrastructure)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 **4개 핵심 목표 완전 달성**

### ✅ **Goal 1: 일일 자동 포트폴리오 포지션 업데이트**
- **IBKR 표준 Excel 형식**: Summary/Matrix 시트 완전 지원
- **SharePoint 자동 업로드**: 날짜별 폴더 구성 및 자동 파일 관리  
- **이메일 첨부파일 전송**: minsu.yeom@arkifinance.com 자동 발송
- **Net Liquidation Value & Securities Gross Position Value**: IBKR 표준 계산
- **Asset Class 매핑**: Universe 데이터 기반 자산 분류

### ✅ **Goal 2: 주문 생성 시스템**
- **모델 포트폴리오 기반**: GTAA B301, Peace of Mind B101 등 지원
- **3가지 주문 유형**: 입금(deposit), 출금(withdrawal), 리밸런싱(rebalance)
- **CSV 주문지 출력**: 바로 실행 가능한 주문 형식
- **현재 포지션 통합**: IBKR API 연동으로 실시간 포지션 반영
- **최소 거래 금액 제어**: 불필요한 소액 거래 방지

### ✅ **Goal 3: 마켓 데이터 플랫폼 분리**  
- **역할 기반 접근 제어**: Portfolio Manager vs Trade Assistant
- **캐시 기반 오프라인 작업**: 실시간 가격 의존성 제거
- **가격 데이터 추적**: 사용된 가격 날짜 명확 표시
- **IBKR Profile 관리**: 사용자 유형별 별도 설정
- **마켓 데이터 신선도 검증**: 24시간 기준 자동 업데이트 판단

### ✅ **Goal 4: 싱가포르 시간대 스케줄링**
- **완전 자동화 일정**: 매일 SGT 6:00 AM (마켓 데이터) + 6:30 AM (포트폴리오)
- **APScheduler 기반**: 안정적인 cron-style 스케줄링
- **다중 배포 옵션**: systemd service, manual daemon, cron 지원
- **포괄적 에러 처리**: 실패 시 자동 이메일 알림
- **프로덕션 데몬 관리**: PID 파일, 로그 관리, 상태 모니터링

## 🚀 **빠른 시작**

### 1. 설치 및 배포
```bash
# 저장소 복제
git clone https://github.com/my2582/simple-order-management-platform.git
cd simple-order-management-platform

# 의존성 설치  
pip install -r requirements.txt

# 프로덕션 배포 (권장)
sudo ./scripts/deploy_scheduler.sh
```

### 2. 자동 스케줄러 시작
```bash
# 방법 1: CLI 명령어로 시작
python3 -m simple_order_management_platform.cli start-scheduler

# 방법 2: 데몬 스크립트로 관리
./scripts/scheduler_daemon.py start

# 방법 3: systemd 서비스 (프로덕션)
sudo systemctl start portfolio-scheduler
sudo systemctl enable portfolio-scheduler  # 부팅 시 자동 시작
```

### 3. 상태 확인 및 모니터링
```bash
# 스케줄러 상태 확인
python3 -m simple_order_management_platform.cli scheduler-status

# 다음 실행 시간 확인
# ✓ Current time (SGT): 2025-09-07 01:12:48 +08
# • Market Data Update: 06:00 SGT daily  
# • Portfolio Update: 06:30 SGT daily
# 🟢 Scheduler Status: RUNNING

# 시스템 통합 테스트
python3 -m simple_order_management_platform.cli test-integrations
```

## 📊 **IBKR 표준 Excel 출력 형식**

### Summary Sheet
| Account | Net Liquidation Value | Securities Gross Position Value | Cash | % of Net Liq |
|---------|----------------------|--------------------------------|------|-------------|
| DU123456| $150,250.00         | $142,750.00                   | $7,500.00 | 95.01% / 4.99% |

### Matrix Sheet  
| Account_ID | Gross/NLV | Cash % | SPY_Weight | QQQ_Weight | IWM_Weight | Asset_Class |
|------------|-----------|--------|------------|------------|------------|-------------|
| DU123456   | 95.01%    | 4.99%  | 33.5%      | 33.2%      | 33.3%      | ETF        |

### 자동 SharePoint 저장 경로
```
/OneDrive-SharedLibraries-OPTIMALVEST/Arki Investment - Trading/
├── 2025-09-06/
│   ├── portfolio_positions_20250906_063000.xlsx  # 매일 6:30 AM 자동 업로드
│   └── market_data_report_20250906_060000.xlsx   # 매일 6:00 AM 자동 업로드
└── simple-order-management-platform/             # 프로젝트 백업
```

## 🛠️ **포괄적 CLI 인터페이스**

### 자동화 및 스케줄링
```bash
# 스케줄러 관리
python3 -m simple_order_management_platform.cli start-scheduler
python3 -m simple_order_management_platform.cli scheduler-status  
python3 -m simple_order_management_platform.cli test-scheduler

# 수동 실행 (스케줄러와 동일한 워크플로우)
python3 -m simple_order_management_platform.cli run-daily-update
python3 -m simple_order_management_platform.cli update-market-data
```

### 포트폴리오 관리
```bash
# IBKR 표준 형식 다운로드 (asset class 매핑 포함)
python3 -m simple_order_management_platform.cli download-positions-ibkr

# 캐시된 가격으로 오프라인 다운로드
python3 -m simple_order_management_platform.cli download-positions-cached

# 특정 계좌만
python3 -m simple_order_management_platform.cli download-positions-ibkr --accounts DU123456,DU789012
```

### 마켓 데이터 관리
```bash
# 마켓 데이터 캐시 상태 확인
python3 -m simple_order_management_platform.cli market-data-status
# Cache Status: FRESH (Age: 2.3 hours)

# Trade Assistant 역할로 마켓 데이터 업데이트
python3 -m simple_order_management_platform.cli update-market-data
```

### 주문 생성 시스템
```bash
# 모델 포트폴리오 기반 주문 생성
python3 -m simple_order_management_platform.cli generate-orders DU123456 B301 --type deposit --amount 25000

# 리밸런싱 주문 (현재 포지션 기반)
python3 -m simple_order_management_platform.cli generate-orders DU123456 B301 --type rebalance --amount 100000

# 출금 주문 (비례 매도)  
python3 -m simple_order_management_platform.cli generate-orders DU123456 B301 --type withdrawal --amount 15000 --proportional
```

### 시스템 관리 및 테스트
```bash
# 전체 통합 테스트
python3 -m simple_order_management_platform.cli test-integrations
# ✅ IBKR Connection: PASSED
# ✅ SharePoint Integration: PASSED  
# ✅ Email Service: PASSED
# ✅ Market Data Cache: PASSED

# 사용 가능한 모델 포트폴리오 확인
python3 -m simple_order_management_platform.cli list-portfolios
```

## ⚙️ **역할 기반 접근 제어**

### Portfolio Manager 역할
- **권한**: 포트폴리오 다운로드, 계좌 요약, 주문 생성
- **IBKR Profile**: `portfolio_manager` (Client ID: 1, 전체 거래 접근)
- **사용 사례**: 일일 포트폴리오 업데이트, 고객 주문 처리

### Trade Assistant 역할  
- **권한**: 마켓 데이터 접근, 가격 다운로드, Universe 업데이트
- **IBKR Profile**: `trade_assistant` (Client ID: 2, 마켓 데이터 전용)
- **사용 사례**: 마켓 데이터 캐시 업데이트, 가격 정보 관리

```yaml
# config/app.yaml 역할 설정
ibkr_profiles:
  portfolio_manager:
    permissions: ["portfolio_download", "order_generation", "account_summary"]
  trade_assistant:  
    permissions: ["market_data", "universe_update", "price_download"]
```

## 📈 **마켓 데이터 캐싱 시스템**

### 캐시 기반 오프라인 작업
```bash
# 캐시 상태 확인
python3 -m simple_order_management_platform.cli market-data-status
# Current time (SGT): 2025-09-07 01:12:48 +08
# Cache Status: FRESH (Age: 2.3 hours)
# Last Updated: 2025-09-06 22:30:15 +08
```

### 자동 신선도 관리
- **24시간 신선도**: 캐시 데이터의 유효성 자동 검증
- **Trade Assistant 업데이트**: 매일 6:00 AM SGT 자동 갱신
- **가격 날짜 추적**: 포트폴리오에 사용된 가격 날짜 명시
- **오프라인 우선**: 실시간 가격 의존성 최소화

## 🕐 **Singapore Timezone 스케줄링**

### 자동화된 일일 스케줄
| 시간 | 작업 | 설명 |
|------|------|------|
| **06:00 SGT** | Market Data Update | Trade Assistant 역할로 전체 Universe 가격 업데이트 |
| **06:30 SGT** | Portfolio Update | Portfolio Manager 역할로 전체 계좌 포지션 다운로드 |

### 포괄적 워크플로우 (매일 06:30 실행)
1. **포지션 다운로드**: IBKR API 연결 및 전체 계좌 데이터 수집
2. **Asset Class 매핑**: Universe 데이터로 ETF/Futures 분류  
3. **Excel 생성**: IBKR 표준 형식 (Summary + Matrix 시트)
4. **SharePoint 업로드**: 날짜별 폴더에 자동 저장
5. **이메일 발송**: 첨부파일 포함 상세 리포트 전송
6. **에러 처리**: 실패 시 자동 알림 및 로그 기록

## 🛠️ **배포 인프라스트럭처**

### 프로덕션 배포 스크립트
```bash
# 원클릭 배포 및 설정
sudo ./scripts/deploy_scheduler.sh

# 배포 옵션 선택:
# 1) systemd service 설치 (권장)
# 2) 수동 데몬 관리
# 3) cron 기반 대안
# 4) 모든 옵션 설치
```

### systemd 서비스 관리
```bash
# 서비스 상태 확인
sudo systemctl status portfolio-scheduler

# 로그 실시간 모니터링  
sudo journalctl -u portfolio-scheduler -f

# 자동 부팅 시 시작
sudo systemctl enable portfolio-scheduler
```

### 수동 데몬 관리
```bash
# 데몬 시작/정지/상태
./scripts/scheduler_daemon.py start|stop|status

# 상세 상태 정보
./scripts/scheduler_daemon.py status
# Status: 🟢 RUNNING
# PID: 12345  
# Uptime: 24.5 hours
# Memory Usage: 156.3 MB
# CPU Usage: 0.2%

# 로그 확인
./scripts/scheduler_daemon.py logs --follow
```

## 📊 **지원하는 모델 포트폴리오**

| Portfolio ID | 전략명 | 구성 종목 | 비중 | 자산 클래스 |
|--------------|--------|-----------|------|-------------|
| **B301** | Future Fund - GTAA | SPMO, SMH, IAU | 33.33% 균등 | ETF |  
| B101 | Peace of Mind | TBD | TBD | Mixed |
| B201 | Income Builder - 1 | TBD | TBD | Fixed Income |
| B202 | Income Builder - 2 | TBD | TBD | Fixed Income |

### 주문 시나리오 지원
- **신규 입금**: 모델 포트폴리오 비중대로 매수 주문 생성
- **리밸런싱**: 현재 포지션 대비 목표 비중 조정 주문
- **출금 처리**: 비례 매도 또는 큰 포지션 우선 매도

## 📁 **전체 프로젝트 구조**

```
simple-order-management-platform/
├── src/simple_order_management_platform/
│   ├── cli.py                          # 포괄적 CLI 인터페이스 (15개 명령어)
│   ├── models/
│   │   ├── portfolio.py                # 포트폴리오 데이터 모델
│   │   ├── orders.py                   # 주문 데이터 모델  
│   │   └── universe.py                 # Asset class 매핑 시스템
│   ├── services/
│   │   ├── portfolio_service.py        # 포트폴리오 다운로드 (캐시 지원)
│   │   ├── order_service.py            # 모델 포트폴리오 기반 주문 생성
│   │   ├── market_data_service.py      # 마켓 데이터 캐싱 및 관리
│   │   ├── automation_service.py       # 완전 자동화 워크플로우
│   │   └── scheduler_service.py        # Singapore timezone 스케줄링
│   ├── auth/
│   │   └── permissions.py              # 역할 기반 접근 제어
│   ├── integrations/
│   │   ├── sharepoint.py               # SharePoint/OneDrive 자동 업로드
│   │   └── email.py                    # Office 365 SMTP 이메일 통합
│   ├── utils/
│   │   ├── exporters.py                # 일반 Excel/CSV 출력
│   │   └── ibkr_exporters.py           # IBKR 표준 형식 Excel 출력
│   └── config/                         # 통합 설정 관리
├── scripts/
│   ├── deploy_scheduler.sh             # 프로덕션 배포 스크립트
│   ├── scheduler_daemon.py             # 데몬 프로세스 관리
│   └── portfolio-scheduler.service     # systemd 서비스 파일
├── docs/
│   └── SCHEDULER_GUIDE.md              # 완전한 스케줄러 가이드
├── config/
│   ├── app.yaml                        # 메인 앱 설정 (역할, 스케줄, 이메일)  
│   └── universes/                      # Asset class 매핑 데이터
├── data/
│   ├── model_portfolios/               # 모델 포트폴리오 정의
│   ├── market_data_cache/              # 마켓 데이터 캐시 저장소
│   └── output/                         # 생성된 파일 출력
└── logs/                               # 스케줄러 및 시스템 로그
```

## 🔍 **모니터링 및 문제 해결**

### 상태 점검 체크리스트
```bash
# 1. 스케줄러 상태 확인  
python3 -m simple_order_management_platform.cli scheduler-status

# 2. 마켓 데이터 캐시 상태
python3 -m simple_order_management_platform.cli market-data-status  

# 3. 전체 통합 테스트
python3 -m simple_order_management_platform.cli test-integrations

# 4. IBKR 연결 테스트
python3 -m simple_order_management_platform.cli test-connection
```

### 로그 파일 위치
- **스케줄러 로그**: `logs/scheduler_daemon.log`
- **에러 로그**: `logs/scheduler_daemon_error.log`  
- **systemd 로그**: `journalctl -u portfolio-scheduler`
- **애플리케이션 로그**: 각 CLI 명령어 실행 시 콘솔 출력

### 일반적인 문제 해결

**1. SharePoint 업로드 실패**
```bash
# OneDrive 동기화 상태 확인
ls -la "/Users/msyeom/Library/CloudStorage/OneDrive-SharedLibraries-OPTIMALVEST.AIPTE.LTD/Arki Investment - Trading"

# 권한 확인 및 수동 테스트  
python3 -m simple_order_management_platform.cli test-integrations
```

**2. 이메일 발송 실패**  
```bash
# EMAIL_PASSWORD 환경변수 설정
export EMAIL_PASSWORD="your-office365-app-password"

# 이메일 연결 테스트
python3 -m simple_order_management_platform.cli test-integrations
```

**3. 마켓 데이터 캐시 문제**
```bash
# 캐시 상태 및 신선도 확인
python3 -m simple_order_management_platform.cli market-data-status

# 강제 캐시 업데이트
python3 -m simple_order_management_platform.cli update-market-data
```

## 🎯 **설계 철학 및 특징**

### Production-Ready 아키텍처
- **무인 자동화**: 수동 개입 없이 24/7 운영
- **에러 복구**: 포괄적 예외 처리 및 자동 알림
- **확장성**: 모듈화된 서비스 구조로 기능 확장 용이
- **보안**: 역할 기반 접근 제어 및 환경변수 기반 인증

### IBKR 표준 준수
- **용어 일치**: Net Liquidation Value, Securities Gross Position Value 등
- **형식 호환**: IBKR 기본 리포트와 동일한 Excel 구조
- **API 최적화**: ib-insync 라이브러리 활용한 안정적 연결

### 실용적 접근
- **Portfolio Manager 중심**: 실제 업무 플로우 최적화
- **Unix 철학**: 각 도구는 하나의 일을 완벽하게 수행
- **즉시 사용**: 복잡한 설정 없이 바로 프로덕션 배포 가능

## 📚 **상세 문서**

- **[📋 스케줄러 완전 가이드](docs/SCHEDULER_GUIDE.md)**: 설치, 배포, 문제 해결
- **[⚙️ CLI 명령어 레퍼런스](docs/cli-reference.md)**: 전체 명령어 상세 설명
- **[🔧 IBKR 연결 설정](docs/ibkr-setup.md)**: Interactive Brokers 설정 가이드
- **[📊 모델 포트폴리오 관리](docs/model-portfolios.md)**: 포트폴리오 정의 및 관리
- **[💼 일일 워크플로우](docs/daily-workflow.md)**: 자동화된 일일 작업 플로우

## 🤝 **기여하기**

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)  
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 **라이선스**

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 **지원**

- **Issues**: GitHub Issues를 통한 버그 리포트 및 기능 요청
- **Documentation**: [docs/](docs/) 디렉토리의 상세 가이드 참조
- **Email**: 시스템 오류 시 자동으로 minsu.yeom@arkifinance.com으로 알림

---

## 🎉 **최근 업데이트 (2025-09-06)**

### 🚀 **v2.0 - 완전 자동화 포트폴리오 관리 플랫폼**
- ✅ **4개 핵심 목표 100% 완성**: 자동화, 주문생성, 데이터분리, 스케줄링
- 🕐 **Singapore Timezone 자동화**: 매일 6:00/6:30 AM 무인 실행
- 📊 **IBKR 표준 Excel 출력**: Summary/Matrix 시트 완전 지원
- 🔐 **역할 기반 접근 제어**: Portfolio Manager vs Trade Assistant
- 📧 **완전 자동화 워크플로우**: SharePoint + Email 통합
- 🛠️ **프로덕션 배포 인프라**: systemd, daemon, cron 다중 지원
- 📱 **15개 CLI 명령어**: 포괄적 관리 및 모니터링 도구

**개발자 노트**: 실제 포트폴리오 매니저의 일일 업무를 완전 자동화하는 프로덕션 레디 플랫폼으로 진화했습니다. 수동 개입 없이 매일 정시에 포트폴리오 리포트가 SharePoint에 저장되고 이메일로 전송됩니다.