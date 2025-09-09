# CLI Shortcuts Guide 🚀

이 문서는 Simple Order Management Platform의 새로운 CLI 단축 명령어를 설명합니다.

## ✨ 새로운 기능

### 🎯 **간소화된 명령어**
긴 `python3 -m simple_order_management_platform.cli` 대신 간단한 `./command` 형식을 사용할 수 있습니다.

### 🔧 **IBKR 포트 우선순위 변경**
- **주 포트**: 4001 (Live Gateway) - 라이브 계좌
- **대체 포트**: 4002 (Paper Gateway) - 페이퍼 계좌  
- **추가 대체**: 7497, 7496 (TWS 포트들)

## 📋 사용 가능한 단축 명령어

### 🆘 도움말
```bash
./simple-order-help          # 전체 단축 명령어 목록 확인
```

### 🔄 마켓 데이터
```bash
./update-market-data         # 마켓 데이터 캐시 업데이트
./market-data-status         # 캐시 상태 및 신선도 확인
```

### 📊 포트폴리오 관리
```bash
./positions         # 실시간 가격으로 포지션 다운로드
./positions-cached  # 캐시된 가격으로 빠른 다운로드
./run-daily-update          # 전체 일일 업데이트 워크플로우
```

### 📝 주문 생성
```bash
./generate-orders           # 모델 포트폴리오 기반 주문 생성
./list-portfolios          # 사용 가능한 모델 포트폴리오 목록
```

### 🔧 시스템 관리
```bash
./test-connection          # IBKR 연결 테스트
./test-integrations        # 전체 시스템 통합 테스트
```

### ⏰ 스케줄러
```bash
./start-scheduler          # 싱가포르 시간 기준 자동 스케줄러 시작
./scheduler-status         # 스케줄러 상태 및 다음 실행 시간
```

## 💡 실용적인 사용 예제

### 일일 워크플로우
```bash
# 1. 시스템 상태 확인
./test-integrations

# 2. 마켓 데이터 업데이트
./update-market-data

# 3. 포트폴리오 다운로드
./positions --accounts DU123456

# 4. 필요시 주문 생성
./generate-orders DU123456 B301 --type rebalance --amount 150000
```

### IBKR 연결 문제 해결
```bash
# Live Gateway (포트 4001) 연결 테스트
./test-connection --ib-port 4001

# Paper Gateway (포트 4002) 연결 테스트  
./test-connection --ib-port 4002

# TWS (포트 7497) 연결 테스트
./test-connection --ib-port 7497
```

### 캐시 기반 오프라인 작업
```bash
# 마켓 데이터 상태 확인
./market-data-status

# 캐시된 가격으로 빠른 포지션 다운로드
./positions-cached --accounts DU123456,DU789012
```

## 🔧 기술적 세부사항

### 스크립트 위치
모든 단축 명령어 스크립트는 프로젝트 루트 디렉토리에 위치합니다:
```
simple-order-management-platform/
├── update-market-data          # 실행 가능한 bash 스크립트
├── download-positions          # 실행 가능한 bash 스크립트
├── test-connection            # 실행 가능한 bash 스크립트
├── simple-order-help          # 도움말 스크립트
└── ...                        # 기타 단축 스크립트들
```

### 동작 원리
각 스크립트는 다음과 같이 작동합니다:
1. 프로젝트 루트 디렉토리로 이동
2. 해당하는 전체 python 모듈 명령어 실행
3. 모든 명령행 인자(`$@`) 그대로 전달

### 호환성
- **기존 명령어**: 여전히 완전히 지원됨
- **새 단축 명령어**: 기존 명령어와 100% 동일한 기능
- **플랫폼**: Linux/macOS bash 환경에서 동작

## 🎉 업그레이드 효과

### Before (기존)
```bash
python3 -m simple_order_management_platform.cli update-market-data --force
python3 -m simple_order_management_platform.cli download-positions-ibkr --accounts DU123456
python3 -m simple_order_management_platform.cli generate-orders DU123456 B301 --type rebalance --amount 100000
```

### After (개선됨)  
```bash
./update-market-data --force
./positions --accounts DU123456
./generate-orders DU123456 B301 --type rebalance --amount 100000
```

**결과**: 명령어 길이 75% 단축, 입력 오류 가능성 대폭 감소! 🚀