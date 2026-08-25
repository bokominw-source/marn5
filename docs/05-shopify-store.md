# 05 · JP Shopify 스토어 구축 현황

> 스토어 `cwx1ii-ku.myshopify.com` (이름 `Marn5_JP`) · 최종 갱신 2026-08-25
> 이 문서는 **실제 스토어에 반영된 상태**를 기록한다. 추측 금지, 조회 결과만 적는다.

---

## 0. 스토어 식별자

| 항목 | 값 |
|---|---|
| myshopify 도메인 | `cwx1ii-ku.myshopify.com` (**변경 불가**) |
| 스토어 이름 | `Marn5_JP` |
| 플랜 | Basic |
| 베이스 테마 | **Horizon** (MAIN) — D6 결정과 일치 |

MCP 커넥터는 **계정당 한 스토어**만 연결된다. 이 스토어에 연결하면 DHALIORA 연결이 끊긴다.
Cowork 에서 DHALIORA 를 쓰려면 그쪽에서 재인증해야 한다.

---

## 1. ★ 미해결 — 스토어 통화가 KRW 다

**이것이 현재 최대 블로커다.** 상품 가격을 JPY 로 넣을 수 없다.

마켓 단위로 JPY 를 붙이려 시도한 결과:

```
marketCreate(currencySettings: {baseCurrency: JPY})
→ "The shop's payment gateway does not support enabling more than one currency."
```

원인: Shopify Payments 가 없어 **다중통화 자체가 불가능**하다.
한국 사업자(736-81-00826)는 Shopify Payments 대상이 아니며, 일본 법인 설립은 Out of Scope 다.

**따라서 해법은 다중통화가 아니라 스토어 기본 통화를 JPY 로 만드는 것 하나뿐이다.**
Settings → Store details → Currency. **API 로는 불가, 관리자에서만 된다.**

> 주문이 1건이라도 생기면 통화 변경이 잠긴다. 현재 주문 0 · 상품 0 이므로 지금이 무손실 창이다.

### 관리자에서만 가능한 나머지 (API 미지원 확인함)

| 항목 | 요구 | 현재 |
|---|---|---|
| 통화 | JPY | `KRW` |
| 기본 언어 | 일본어 | `en` (일본어는 **보조 로케일로 게시됨**) |
| 시간대 | Asia/Tokyo | `Asia/Seoul` |
| 중량 단위 | g | `KILOGRAMS` |
| 사업장 국가 | — | `South Korea` (한국 법인이므로 **정상**, 변경 대상 아님) |

`shopLocaleUpdate` 에 `primary` 필드가 없다 → 기본 언어 전환은 API 불가.

---

## 2. 반영 완료 (API)

### 마켓
| | |
|---|---|
| `gid://shopify/Market/60297904282` | **Japan** (`jp`) · ACTIVE · 조건 = 국가 JP |
| 세금 | `INCLUDES_TAXES_IN_PRICE` — 일본 総額表示義務 대응 |
| 관세 | `INCLUDE_DUTIES_IN_PRICE` — **DDP**. Basic 플랜에서 수락됨 |
| `gid://shopify/Market/60297019546` | South Korea (`kr`) — 스토어 생성 시 기본. 정리 필요 |

> 관세 **가격 전략**은 설정됐다. 체크아웃에서 실제로 관세가 **계산·징수**되는지는
> HS코드·원산지 입력과 캐리어 DDP 지원이 전제이며 아직 검증 불가.

### 로케일
`ja` (Japanese) 추가 · **published** · primary 아님(§1 참조)

### 메타필드 정의 8종 (`01-audit.md` 의 P0/P1)
| 키 | 타입 | 핀 |
|---|---|---|
| `custom.material_composition` | single_line_text_field | ● |
| `custom.care_symbols` | list.single_line_text_field | ● |
| `custom.label_holder` | single_line_text_field | ● |
| `custom.size_chart_cm` | json | ● |
| `custom.jp_size_map` | json | ● |
| `custom.fit_index` | json | |
| `custom.rcep_origin` | boolean | |
| `custom.duty_exempt_class` | single_line_text_field | |

전부 **값은 비어 있다.** 원자료(소재조성·취급표시·사이즈표·원산지)가 미확보이기 때문이다.

### 컬렉션 5종 (§12 IA)
`bra` ブラ · `shorts` ショーツ · `inner` インナー · `leg` レッグ · `homewear` ホームウェア
전부 MANUAL 정렬. 상품 미배정.

### 페이지 4종
| 핸들 | 제목 | 게시 |
|---|---|---|
| `size-guide` | サイズガイド | 게시 (승인 대기 표시 포함) |
| `shipping-duties` | 配送・関税について | 게시 (¥8,800 · DDP 고지) |
| `returns` | 返品・交換について | **미게시** — 일본 반품 수취지 미확보 |
| `legal` | 特定商取引法に基づく表記 | **미게시** — 법무 확인 전 |

전부 **골격**이다. 확정 문안이 아니며 「記入待ち」「監修待ち」로 표시돼 있다.

### 내비게이션
GNB (§12 의 6+1 그대로):
`ブラ / ショーツ / インナー / レッグ / ホームウェア / サイズガイド / 配送状況`
`配送状況` 는 최상위 고정 (越境EC 문의 1위).

푸터: 配送・関税 / サイズガイド / 返品・交換 / 特商法 / お問い合わせ

---

## 3. 상품 — 투입 대기

`scripts/build_product_inputs.py` 로 41/41 · variant 183 생성 완료 (`out/product_inputs.json`).
**통화가 JPY 로 바뀔 때까지 투입하지 않는다.**

적용한 정규화:
- **P0-1** `103`·`139` 를 `유발/무발` 축으로 분리 → 3옵션 한계 준수. 옵션 3개 초과 상품 **0건**
- **P0-2** 옵션값의 `[10%]` 할인 표기 제거
- **P1-4** 음수 재고 **134건**을 0 으로 클램프 (원값은 `negative_stock_source` 에 보존)
- **P1-5** 카페24 태그 **미이관**

의도적으로 보류한 것:
- **일본어 상품명** — 무감수 자동번역 금지(§13). 한국어 원문 유지 + **전 상품 DRAFT**
- **JPY 가격** — 환산값은 자리표시자. 정가표는 별도 확정 대상
- **메타필드 값** — 원자료 미확보

> variant 183 은 **하한**이다. Catalog MCP 가 상품당 5건만 반환하고, 41건 중 **30건이 상한에 걸렸다.**
> 실제 조합은 훨씬 많다. Admin API 전량 추출 후 재생성해야 한다.

---

## 4. 다음 할 일

1. **[발주자] 통화 KRW → JPY** ← 다른 모든 것이 여기 걸려 있다
2. [발주자] 기본 언어 일본어 · Asia/Tokyo · 중량 g · 한국 마켓 정리
3. 통화 전환 후 41 SKU DRAFT 투입 → 컬렉션 배정 → diff 검증
4. Shopify 지원 확인: Basic 플랜에서 체크아웃 관세 징수가 실제로 동작하는가
5. 결제 — 일본 결제대행사 계약 진행 중. 확정 시 D3 갱신
6. Horizon 커스텀 섹션 (P0-3 브라→쇼츠 추가구매)
7. 네이티브 카피 확보 후 `translationsRegister`
