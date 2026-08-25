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

MCP 커넥터는 **계정당 한 스토어**만 연결된다. 이 스토어에 연결하면 DHALIORA 연결이 끊기고,
Cowork 에서 DHALIORA 로 재인증하면 **이쪽 연결이 조용히 바뀐다.**

> ⚠ **쓰기 작업 전에는 반드시 `shop { name myshopifyDomain }` 으로 대상을 확인할 것.**
> 실제로 태그 부여 중 커넥터가 DHALIORA 로 바뀌어 있어 mutation 이 전량 실패한 적이 있다
> (2026-08-25). 상품 ID 가 달라 무해하게 튕겼지만, 운이 좋았던 것이다.

---

## 1. 통화 — JPY 로 전환 완료 (2026-08-25)

발주자가 관리자에서 전환했고, 41 SKU 는 JPY 로 투입됐다.
**아래는 왜 다중통화로는 안 됐는지의 기록이다. 스토어를 다시 만들 일이 있으면 반드시 읽을 것.**

마켓 단위로 JPY 를 붙이려 시도한 결과:

```
marketCreate(currencySettings: {baseCurrency: JPY})
→ "The shop's payment gateway does not support enabling more than one currency."
```

원인: Shopify Payments 가 없어 **다중통화 자체가 불가능**하다.
한국 사업자(736-81-00826)는 Shopify Payments 대상이 아니며, 일본 법인 설립은 Out of Scope 다.

**따라서 해법은 다중통화가 아니라 스토어 기본 통화를 JPY 로 만드는 것 하나뿐이었다.**
Settings → Store details → Currency. **API 로는 불가, 관리자에서만 된다.**

> 주문이 1건이라도 생기면 통화 변경이 잠긴다. 상품 투입 전에 끝낸 것이 맞다.

### 관리자에서만 가능한 나머지 (API 미지원 확인함)

| 항목 | 요구 | 현재 | 판정 |
|---|---|---|---|
| 통화 | JPY | ✅ `JPY` | 해결 |
| **기본 언어** | **일본어** | `en` (일본어는 보조 로케일) | **실제 과제** |
| 한국 마켓 | 제거 | `South Korea (kr)` ACTIVE | 정리 권장 |
| 시간대 | — | `Asia/Seoul` | **바꿀 필요 없음** |
| 중량 단위 | — | `KILOGRAMS` | **바꿀 필요 없음** |
| 사업장 국가 | — | `South Korea` | 한국 법인이므로 정상 |

`shopLocaleUpdate` 에 `primary` 필드가 없다 → 기본 언어 전환은 API 불가, 관리자에서만 된다.
Translate & Adapt 는 **기본 언어 위에** 번역을 얹는 구조라, 기본이 영어면 일본어가 계속 번역본 취급을 받는다.

> **정정 (2026-08-25)**: 이 표에 원래 시간대와 중량 단위가 "고쳐야 할 항목"으로 들어가 있었다. 둘 다 근거가 없다.
> - **시간대**: KST 와 JST 는 **둘 다 UTC+9 이고 서머타임이 없다.** 오프셋이 동일하므로
>   주문 타임스탬프 · 리포트 일자 경계 · 예약 발행이 전부 같게 계산된다. 바꿀 이유가 없고,
>   애초에 "되돌리기 어려운 설정"도 아니다 (언제든 변경 가능).
> - **중량 단위**: 관세·배송비 계산에 들어가는 것은 **중량값이지 표시 단위가 아니다.**
>   Shopify 는 소수를 받으므로 40g 을 `0.04 kg` 로 넣어도 결과가 같다. 신규 입력 시 편의 문제일 뿐이다.
>
> 인수인계 문서(`CLAUDE.md` §10)의 목록을 검증 없이 옮긴 것이 원인이다.

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
| 핸들 | 표기 | 배정된 상품 |
|---|---|---|
| `bra` | ブラ | 12 (브라 8 + 누드브라 4) |
| `shorts` | ショーツ | 7 |
| `inner` | インナー | 12 (캡나시 6 + FW 6) |
| `leg` | レッグ | 9 |
| `homewear` | ホームウェア | 0 — MVP 41 에 해당 품목이 없다 |

전부 MANUAL 정렬. `homewear` 는 GNB 에 있으나 비어 있으므로 **공개 전 상품 배정 또는 메뉴 제외**가 필요하다.

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

## 3. 상품 — 41/41 투입 완료 (2026-08-25)

`scripts/build_product_inputs.py` → `scripts/make_batches.py` → `productSet` 로 투입.
**상품 41 · variant 183 · 전부 DRAFT · 가격 ¥676〜¥3,769 (JPY) · 이미지 41건 READY.**

적용한 정규화:
- **P0-1** `103`·`139` 를 `유발/무발` 축으로 분리 → 3옵션 한계 준수. 옵션 3개 초과 상품 **0건**
- **P0-2** 옵션값의 `[10%]` 할인 표기 제거
- **P1-4** 음수 재고 **134건**을 0 으로 클램프 (원값은 `negative_stock_source` 에 보존)
- **P1-5** 카페24 태그 **미이관** → 일본용 태그를 새로 부여 (아래)

### 분류 태그 부여 완료 (2026-08-25, 41/41 검증)
| 태그 | 건수 | | 태그 | 건수 |
|---|---|---|---|---|
| `bra` | 12 | | `leg` | 10 |
| `nudebra` | 4 | | `stockings` | 5 |
| `shorts` | 7 | | `socks` | 5 |
| `inner` | 12 | | `cami` | 6 |
| | | | `thermal` | 6 |

`stockings`/`socks` 분리는 관세 때문이다 (스타킹 과세 / 양말 면세 가능).
상세는 `06-ia-collections.md`.

의도적으로 보류한 것:
- **일본어 상품명** — 무감수 자동번역 금지(§13). 한국어 원문 유지 + **전 상품 DRAFT**
- **JPY 가격** — 환산값은 자리표시자. 정가표는 별도 확정 대상
- **메타필드 값** — 원자료 미확보

> variant 183 은 **하한**이다. Catalog MCP 가 상품당 5건만 반환하고, 41건 중 **30건이 상한에 걸렸다.**
> 실제 조합은 훨씬 많다. Admin API 전량 추출 후 재생성해야 한다.

### 투입하면서 확인한 Shopify 제약
- **옵션명 중복 불가** — 축 역할이 겹치는 상품(`pack × color × color` 등 4건)은 뒤에 번호를 붙인다 (`カラー 2`)
- **옵션 없는 상품도 `productOptions` 필수** — `Title` / `Default Title` 을 명시해야 한다 (`713`)
- **`productSet` 은 handle 로 기존 상품을 갱신하지 않는다** — `HANDLE_NOT_UNIQUE` 로 거부된다.
  재투입·수정에는 `id` 가 필요하다. 부분 수정은 `productUpdate` / `productOptionUpdate` 가 가볍다.

### 투입 중 발생한 사고 (해소됨)
MCP 로 값을 넘기는 과정에서 한글이 깨져 **제목 16건 · 옵션값 4건**이 잘못 들어갔다
(`넉넉→넘넘`, `캡나시→칡나시`, `스타킹→스키킹`, `숏→옷`, `여성→여졁`, `컬러별→컴러별`).
`data/details.json` 원본과 전량 대조해 `productUpdate` · `productOptionUpdate` 로 정정하고 재확인했다.
**재발 방지**: 배치 값은 손으로 옮겨 적지 말고 스크립트 출력을 그대로 쓸 것. 투입 후에는 반드시 원본과 diff 한다.

---

## 4. 다음 할 일

1. **[발주자] 기본 언어를 일본어로** ← 관리자에서만 가능. 번역 작업의 전제다
2. [발주자] 한국 마켓(`kr`) 정리 — 일본 전용 스토어인데 한국 배송 대상으로 남아 있다
3. Shopify 지원 확인: Basic 플랜에서 체크아웃 관세 징수가 실제로 동작하는가
4. 결제 — 일본 결제대행사 계약 진행 중. 확정 시 D3 갱신
5. Horizon 커스텀 섹션 (P0-3 브라→쇼츠 추가구매)
6. 네이티브 카피 확보 후 `translationsRegister` → DRAFT 해제
7. JPY 정가표 확정 (현재는 환산 자리표시자)
