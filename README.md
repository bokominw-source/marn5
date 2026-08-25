# marun5-jp

마른파이브(marun5.com · 카페24) → 일본어·JPY Shopify 스토어 이관 프로젝트.

**먼저 `CLAUDE.md` 를 읽을 것.** 프로젝트의 사실·결정·제약이 전부 거기 있다.

```
CLAUDE.md              프로젝트 컨텍스트 (Claude Code 자동 로드)
docs/
  01-audit.md          카페24 현행 감사 · cate_no 전수 · 데이터 매핑
  02-decisions.md      결정 로그 (새 결정은 여기에 추가)
  03-jp-tax-duty.md    일본 관세·소비세 계산 구조와 제도 타임라인
  04-open-questions.md 미해결 · 발주자 요청 항목
  05-shopify-store.md   JP Shopify 스토어 구축 현황 (실반영 상태)
data/
  mvp41.csv            발주자 제출 MVP 41 SKU
  products_41.csv      41건 실측 (가격·옵션축·태그·이미지)
  variants_183.csv     옵션 조합 183건 (재고 포함)
  details.json         Catalog MCP 원본 응답
scripts/
  options.py           옵션 문자열 파서 · 정규화 · 축 역할 판정
  cafe24_catalog.py    Catalog MCP 클라이언트 (인증 불필요)
  rebuild_from_details.py  원본 응답 → CSV 재생성 (네트워크 불요)
  build_product_inputs.py  → Shopify productSet 입력 생성 (네트워크 불요)
  cafe24_extract.py    Admin API 추출기 (OAuth 필요, 로컬 실행용)
design/
  jp-home.html         일본 홈 디자인안 (풀사이즈)
  audit-report.html    감사 리포트 v2
assets/
  marn5-logo.png       투명 배경 워드마크
```

## 빠른 시작

```bash
# 지금 바로 되는 것 — 카페24 상품 데이터 재수집 (인증 불필요)
python3 scripts/cafe24_catalog.py data/mvp41.csv out/

# Admin API 전량 추출 (로컬 PC 에서, 앱 발급 후)
cp .env.example .env      # client_id / secret 채우기
python3 scripts/cafe24_extract.py auth --mall m5m5m5 --client-id XXX --client-secret YYY
python3 scripts/cafe24_extract.py pull --mall m5m5m5 --out out/admin
```

## 주의

- `.env` 와 `.cafe24_token.json` 은 커밋하지 않는다 (`.gitignore` 등록됨)
- 연결된 Shopify 스토어가 **DHALIORA** 라면 마른파이브 스토어가 아니다. 상품을 만들지 말 것
- 일본 법령 판단은 전부 "검토 필요"로 표기한다. 법률 자문이 아니다
