# Simple Order Management Platform 📊

> 리눅스의 "1개의 일을 정말 잘하자" 철학을 적용한 IBKR 포트폴리오 관리 플랫폼

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![IBKR](https://img.shields.io/badge/IBKR-API-green.svg)](https://interactivebrokers.github.io/tws-api/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 핵심 기능

### 📈 1. 일일 포트폴리오 다운로드
- **통합 엑셀 출력**: 모든 계좌의 포지션을 하나의 매트릭스 테이블로 출력
- **실시간 IBKR 데이터**: Live 시장 데이터와 포지션 정보 자동 수집
- **비중 계산**: 위험자산 비중, 현금 비중 자동 계산
- **IBKR 표준 용어**: Net Liquidation Value 등 IBKR 표준 용어 사용

### ⚖️ 2. 모델 포트폴리오 기반 주문 생성
- **GTAA 전략**: B301 Future Fund (SPMO, SMH, IAU 동일 비중)
- **입금/출금/리밸런싱**: 모든 시나리오 지원
- **CSV 주문지**: 바로 실행 가능한 주문 형식 출력

### 🖥️ 3. 단순한 CLI 인터페이스
- **Unix 철학**: 각 명령어는 하나의 작업만 완벽하게 수행
- **타입 안전**: Pydantic 모델로 데이터 검증
- **Rich 출력**: 컬러풀하고 읽기 쉬운 터미널 출력

## 🚀 빠른 시작

### 설치
```bash
git clone https://github.com/my2582/simple-order-management-platform.git
cd simple-order-management-platform
pip install -e .
```

### 기본 사용법
```bash
# 1. IBKR 연결 테스트
simple-order test-connection

# 2. 모든 계좌 포지션 다운로드 (통합 매트릭스 형식)
simple-order download-positions

# 3. GTAA 전략으로 $10,000 신규 투자 주문지 생성
simple-order generate-orders DU123456 B301 --type deposit --amount 10000

# 4. 사용 가능한 모델 포트폴리오 확인
simple-order list-portfolios
```

## 📊 새로운 통합 포지션 매트릭스

### Excel 출력 구조 (v2.0)
기존의 계좌별 개별 탭에서 **통합 매트릭스** 형식으로 완전히 개선:

#### Portfolio_Matrix Sheet
| Account_ID | Net_Liquidation_Value | Risk_Asset_Pct | Cash_Pct | Cash_Base_Currency | Cash_Local_Currency | SPMO_Weight | SMH_Weight | IAU_Weight |
|------------|----------------------|----------------|----------|-------------------|--------------------|-----------  |------------|------------|
| DU123456   | $100,000.00         | 85.5%          | 14.5%    | $14,500.00        | $14,500.00         | 28.5%      | 28.0%      | 29.0%      |
| DU789012   | $250,000.00         | 92.1%          | 7.9%     | $19,750.00        | $19,750.00         | 31.2%      | 30.8%      | 30.1%      |

#### 주요 특징
- **단일 테이블**: 모든 계좌 정보가 한 눈에 보임
- **행**: 계좌 ID
- **열**: 포지션 심볼 + 메타데이터
- **값**: 포지션 비중 (%)
- **IBKR 표준 용어**: Net Liquidation Value, 위험자산 비중, 현금 비중

## 📖 상세 문서

- [📋 전체 CLI 명령어 가이드](docs/cli-reference.md)
- [⚙️ 설치 및 설정](docs/installation.md)
- [🔧 IBKR 연결 설정](docs/ibkr-setup.md)
- [📊 모델 포트폴리오 관리](docs/model-portfolios.md)
- [💼 일일 워크플로우](docs/daily-workflow.md)

## 🛠️ CLI 명령어 요약

### 포트폴리오 관리
```bash
# 포지션 다운로드 (통합 매트릭스)
simple-order download-positions [OPTIONS]

# 특정 계좌만
simple-order download-positions --accounts DU123456,DU789012

# 출력 파일명 지정
simple-order download-positions --output "daily_positions.xlsx"
```

### 주문 생성
```bash
# 입금 주문지
simple-order generate-orders ACCOUNT_ID PORTFOLIO_ID --type deposit --amount AMOUNT

# 리밸런싱 주문지
simple-order generate-orders ACCOUNT_ID PORTFOLIO_ID --type rebalance --amount AMOUNT

# 출금 주문지 (비례 매도)
simple-order generate-orders ACCOUNT_ID PORTFOLIO_ID --type withdrawal --amount AMOUNT --proportional

# 출금 주문지 (큰 포지션부터)
simple-order generate-orders ACCOUNT_ID PORTFOLIO_ID --type withdrawal --amount AMOUNT --largest-first
```

### 정보 조회
```bash
# IBKR 연결 테스트
simple-order test-connection

# 모델 포트폴리오 목록
simple-order list-portfolios

# 전략 목록
simple-order list-strategies

# 마스터 데이터 상태
simple-order list-master
```

## ⚡ 일일 워크플로우 예시

```bash
# 아침 루틴: 모든 계좌 포지션 체크
simple-order download-positions --output "positions_$(date +%Y%m%d).xlsx"

# 고객 입금 처리
simple-order generate-orders DU123456 B301 --type deposit --amount 25000

# 월말 리밸런싱
simple-order generate-orders DU123456 B301 --type rebalance --amount 100000 --min-trade 100

# 출금 요청 처리
simple-order generate-orders DU123456 B301 --type withdrawal --amount 15000 --proportional
```

## 🎯 지원하는 모델 포트폴리오

| Portfolio ID | 전략명 | 구성 종목 | 비중 |
|--------------|--------|-----------|------|
| **B301** | Future Fund - GTAA | SPMO, SMH, IAU | 33.33% 균등 |
| B101 | Peace of Mind | - | - |
| B201 | Income Builder - 1 | - | - |
| B202 | Income Builder - 2 | - | - |

## 🔧 전제 조건

1. **IBKR IB Gateway/TWS 실행 중**
2. **Python 3.9+ 환경**
3. **패키지 의존성**:
   - `ib-insync>=0.9.86`
   - `pandas>=2.0.0`
   - `openpyxl>=3.1.0`
   - `pydantic>=2.0.0`
   - `typer[all]>=0.9.0`

## 📁 프로젝트 구조

```
simple-order-management-platform/
├── src/simple_order_management_platform/
│   ├── cli.py                    # CLI 진입점
│   ├── models/                   # Pydantic 데이터 모델
│   │   ├── portfolio.py          # 포트폴리오 관련 모델
│   │   └── orders.py             # 주문 관련 모델
│   ├── services/                 # 비즈니스 로직
│   │   ├── portfolio_service.py  # 포트폴리오 다운로드
│   │   └── order_service.py      # 주문 생성
│   ├── utils/                    # 유틸리티
│   │   ├── exporters.py          # Excel/CSV 출력
│   │   └── ibkr_client.py        # IBKR 연결 관리
│   └── config/                   # 설정 관리
├── data/
│   ├── model_portfolios/         # 모델 포트폴리오 정의
│   └── output/                   # 출력 파일들
├── config/                       # 앱 설정 파일
├── docs/                         # 상세 문서
└── tests/                        # 테스트 파일
```

## 🔍 문제 해결

### 일반적인 문제들

**1. IBKR 연결 실패**
```bash
# 연결 테스트
simple-order test-connection

# 설정 확인
cat config/app.yaml
```

**2. 계좌 접근 권한**
- IB Gateway에서 관리 계좌 권한 설정 확인
- Client ID 충돌 확인

**3. 최소 거래 금액**
```bash
# 리밸런싱 시 최소 거래 금액 조정
simple-order generate-orders ACCOUNT B301 --type rebalance --amount 50000 --min-trade 100
```

### 로그 및 디버깅
- 모든 작업은 상세 로그로 기록
- Rich 라이브러리로 컬러풀한 출력
- Pydantic으로 데이터 검증 및 오류 메시지

## 🎯 설계 철학

### Unix Philosophy 적용
- **Do One Thing Well**: 각 명령어는 하나의 작업만 완벽하게 수행
- **Composable**: 명령어들을 조합하여 복잡한 워크플로우 구성 가능
- **Predictable Output**: 일관되고 예측 가능한 출력 형식
- **Simple Interface**: 복잡성을 숨기고 단순한 인터페이스 제공

### 실용적 접근
- **Portfolio Manager 중심**: 실제 포트폴리오 매니저의 일일 업무에 최적화
- **IBKR 표준**: Interactive Brokers의 표준 용어와 형식 사용
- **즉시 사용 가능**: 복잡한 설정 없이 바로 사용 가능한 도구

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

- **Issues**: GitHub Issues를 통한 버그 리포트 및 기능 요청
- **Documentation**: [docs/](docs/) 디렉토리의 상세 가이드 참조

---

**개발자 노트**: 실제 포트폴리오 매니저의 니즈를 반영한 실용적인 도구로 설계되었습니다.
**최근 업데이트**: 2025-09-06 - 통합 포지션 매트릭스 기능 추가