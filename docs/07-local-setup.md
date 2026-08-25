# 07 · 로컬 개발 환경 셋업

> 클라우드 컨테이너 → **로컬 PC** 로 옮기는 절차.
> 작성 2026-08-25 · 대상: 발주자 PC 또는 개발자 PC

---

## 왜 옮기는가

클라우드 컨테이너에서 막혀 있던 것들이 로컬에서는 그냥 된다.

| 막혀 있던 것 | 영향 |
|---|---|
| `*.cafe24api.com` 차단 | **§8 런칭 차단 P0 의 절반이 여기 걸려 있다** — 원산지·HS코드·소재조성·실측 사이즈표·전체 variant·리뷰 62,140건 |
| 임의 도메인 차단 | 레퍼런스 사이트 조사 불가 |
| Shopify CLI 없음 | 테마를 저장할 때마다 커밋→업로드→새로고침. `theme dev` 를 쓰면 즉시 반영 |
| staged upload 불가 | 바이너리를 넣으려고 **저장소를 public 으로 열어 둔 상태**다 (`02-decisions.md` 08-25). 로컬이면 이 전제가 사라진다 |

**Catalog MCP 로 뽑은 현재 데이터는 불완전하다.** 상품당 variant 를 최대 5건만 주기 때문에
`variants_183.csv` 의 183건은 실제 조합 수가 아니다. 옵션 재설계(P0-1/2)를 확정하려면
Admin API 전량 추출이 선행돼야 한다.

---

## 0. 준비물

| | 확인 |
|---|---|
| Python **3.8+** | `python3 --version` |
| Node.js **18+** | `node --version` |
| git | `git --version` |
| 카페24 **운영몰 관리자 권한** | 앱 승인에 필요 (§3 참조) |

macOS 에서 없으면:

```bash
# Homebrew 가 없다면 먼저
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python node git
```

Windows 는 [python.org](https://www.python.org/downloads/) · [nodejs.org](https://nodejs.org/) 설치본을 쓴다.
Python 설치 시 **"Add Python to PATH"** 를 반드시 체크할 것.

---

## 1. 저장소 받기

```bash
git clone https://github.com/bokominw-source/marn5.git
cd marn5
git checkout claude/cowork-learning-7n35lv
```

`CLAUDE.md` 가 루트에 있으므로 이 폴더에서 Claude Code 를 실행하면
프로젝트 컨텍스트를 자동으로 읽는다. **인수인계 과정이 따로 없다.**

---

## 2. Claude Code 설치

```bash
npm install -g @anthropic-ai/claude-code
cd marn5
claude
```

첫 실행에서 로그인한다. 실행 폴더가 `marn5` 여야 `CLAUDE.md` 를 읽는다.

### 확인

세션이 열리면 이걸 먼저 시킨다.

```
CLAUDE.md 읽고, curl -I https://m5m5m5.cafe24api.com 로 차단 여부부터 확인해라
```

`HTTP/1.1 401` 이나 `403` 이 나오면 **연결은 되는 것**이다 (인증만 없는 상태).
`curl: (7)` · `(28)` · `CONNECT tunnel failed` 가 나오면 네트워크가 여전히 막혀 있다.

---

## 3. 카페24 Admin API 앱 발급 ★ 여기가 제일 자주 막힌다

### 3-1. mall_id 를 틀리지 말 것

```
mall_id = m5m5m5      ← 이것
도메인   = marun5.com  ← 이게 아님
```

`marun5` 를 넣으면 존재하지 않는 몰에 인증을 시도한다. 스크립트에도 경고를 넣어 뒀다.

### 3-2. 앱 생성

1. [developers.cafe24.com](https://developers.cafe24.com) 로그인
2. **앱 만들기**
3. **Redirect URL** 에 정확히 이 값을 등록

   ```
   http://localhost:8724/callback
   ```

4. **Scope** 체크

   | Scope | 쓰는 곳 |
   |---|---|
   | `mall.read_store` | 몰 기본 정보 |
   | `mall.read_category` | 카테고리 전수 (IA 매핑) |
   | `mall.read_product` | **상품·옵션·variant·재고** ← 핵심 |
   | `mall.read_community` | 리뷰 게시판 |
   | `mall.read_order` | 12개월 판매데이터 (필요 시) |

5. `Client ID` / `Client Secret` 복사

### 3-3. 승인은 운영몰 관리자로 해야 한다

카페24 OAuth 는 **몰 단위**다.

- `marun5jp` 계정으로 앱을 발급받아도 **`m5m5m5` 데이터는 못 읽는다**
- 브라우저 인증 화면이 뜰 때 **`m5m5m5` 운영몰 관리자로 로그인된 상태**여야 한다
- 다른 계정으로 로그인돼 있으면 시크릿 창에서 진행할 것

### 3-4. 자격증명 저장

```bash
cp .env.example .env
```

`.env` 를 열어 채운다.

```
CAFE24_MALL_ID=m5m5m5
CAFE24_CLIENT_ID=여기
CAFE24_CLIENT_SECRET=여기
CAFE24_REDIRECT_URI=http://localhost:8724/callback
```

`.env` 와 `.cafe24_token.json` 은 `.gitignore` 에 등록돼 있다. **절대 커밋하지 않는다.**

> 발주자가 과거에 카페24 관리자 ID/PW 를 채팅에 평문 공유한 이력이 있다.
> **로테이트 권고는 전달했고 해당 자격증명은 사용하지 않았다.** (`CLAUDE.md` §3)
> 카페24 인증은 비밀번호가 아니라 `client_id`/`client_secret` + OAuth 로 한다.

---

## 4. 첫 추출

### 4-1. 인증 (브라우저 1회)

```bash
python3 scripts/cafe24_extract.py auth \
  --mall m5m5m5 \
  --client-id "$CAFE24_CLIENT_ID" \
  --client-secret "$CAFE24_CLIENT_SECRET"
```

브라우저가 열리고 승인하면 `localhost:8724` 로 콜백이 돌아온다.
성공하면 `.cafe24_token.json` 이 생긴다. 이후 만료는 자동 갱신된다.

**브라우저가 안 열리면** 터미널에 찍힌 URL 을 직접 붙여 넣는다.
**8724 포트가 이미 쓰이는 중이면** `--redirect-uri` 를 바꾸고 개발자센터에도 같은 값으로 다시 등록한다.

### 4-2. 소량으로 먼저 확인

전량부터 돌리지 말 것. 41건 중 3건만 뽑아 형태를 본다.

```bash
python3 scripts/cafe24_extract.py pull \
  --mall m5m5m5 --out ./cafe24_dump_test \
  --only 1140,103,2065
```

`1140`(브라) · `103`(4축 상품) · `2065`(태그 오염 사례) 는 각각 알려진 문제를 대표한다.

### 4-3. 전량

```bash
python3 scripts/cafe24_extract.py pull --mall m5m5m5 --out ./cafe24_dump
```

산출물:

```
cafe24_dump/
  categories.json   카테고리 전수 (현행 51개 → 일본 6+1 매핑 검증용)
  products.json     상품 전수
  variants.json     ★ 전체 variant — Catalog MCP 의 5건 제한이 없다
  options.json      상품별 옵션 정의
  reviews.json      리뷰 게시판
  products.csv / variants.csv
  _meta.json
```

리뷰가 필요 없으면 `--board 0`. 62,140건이라 시간이 오래 걸린다.

---

## 5. Shopify CLI (테마 개발)

```bash
npm install -g @shopify/cli@latest
cd marn5/theme
shopify theme dev --store cwx1ii-ku.myshopify.com
```

로컬 서버가 뜨고 파일을 저장할 때마다 즉시 반영된다.

### 주의 — 되돌리기 어려운 사고를 막는 것

| | |
|---|---|
| 작업 대상 | **`Marn5 JP — dev` (`156495577242`, 미게시)** |
| 손대지 않는 것 | `Horizon` (`156492169370`, **라이브**) |

`shopify theme push` 는 **`--theme` 를 반드시 지정한다.** 생략하면 라이브 테마를 물을 수 있다.

```bash
shopify theme pull --theme 156495577242    # 원격 → 로컬
shopify theme push --theme 156495577242    # 로컬 → 원격
```

`theme/` 폴더에는 현재 우리가 만든 파일만 있다(`sections/marn5-hero.liquid`,
`templates/index.json`, `config/settings_data.json`). **먼저 `pull` 로 전체를 받아 온 뒤**
작업하는 게 안전하다.

---

## 6. 옮기고 나서 할 일

셋업이 끝나면 Claude 에게 순서대로 시킨다.

1. **전량 추출** — `cafe24_dump/` 확보
2. **옵션 재설계 재검증** — 진짜 variant 수로 P0-1(4축)·P0-2(할인표기)·P1-4(음수재고) 다시 판정.
   지금 판정은 상품당 5건 표본 위에서 나온 것이다
3. **메타필드 채우기** — 원산지·HS코드·소재조성·실측 사이즈표.
   §8 P0 1~3 이 여기서 풀린다
4. **저장소 비공개 전환 검토** — staged upload 가 되면 public 전제가 사라진다.
   계약 방어 조항·미확인 법적 리스크(DISNEY 라이선스)가 공개돼 있는 상태다
5. **테마 개발** — 헤더 · 폰트 · 모바일 히어로 · 추가구매 섹션(P0-3)

---

## 7. 클라우드 세션은 남겨 둔다

둘 다 같은 저장소를 본다. 충돌하지 않는다.

| | 쓰는 곳 |
|---|---|
| **로컬** | 개발 · 카페24 추출 · 테마 실시간 작업 |
| **클라우드 / Cowork** | 이동 중 문서 검토 · 발주자 커뮤니케이션 · 레퍼런스 조사 |

작업을 끝낼 때마다 push 하면 어느 쪽에서 열어도 이어진다.
클라우드 컨테이너는 비활동 시 회수되므로 **커밋하지 않은 것은 사라진다.**
