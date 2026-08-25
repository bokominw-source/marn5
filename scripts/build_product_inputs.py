#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/details.json → Shopify `productSet` 입력 JSON 생성
=======================================================
네트워크 불요. 생성된 JSON 을 MCP/Admin API 로 흘려 넣는다.

    python3 scripts/build_product_inputs.py           # out/product_inputs.json

적용하는 정규화 (docs 의 P0/P1 대응)
-----------------------------------
P0-1  4축 상품은 `toe`(유발/무발) 축을 기준으로 **별도 상품으로 분리**
      → Shopify 3옵션 한계 준수
P0-2  옵션값에 박힌 `[10%]` 할인 표기 제거
      (Shopify 재현 불가 · 일본에서 비교가격 근거 요구 대상)
P1-4  음수 재고를 0 으로 클램프. 해당 SKU 는 별도 표시
P1-5  카페24 태그는 **이관하지 않는다** (검색용 무관 태그·셀럽 이름 오염)

의도적으로 보류한 것
--------------------
- 일본어 상품명: 무감수 자동번역 금지(§13). 한국어 원문을 그대로 두고
  **전 상품 DRAFT** 로 만든다. 네이티브 카피 확정 후 translationsRegister.
- JPY 가격: 환산값은 **자리표시자**다. 정가표는 별도 확정 대상이며
  자동 환산 게재는 금지(01-audit.md).
- 원산지·HS코드·소재조성·사이즈표: 원자료 미확보. 메타필드는 비워 둔다.
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from options import classify_axes, normalize_value, split_options

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRW_PER_100JPY = 873.0

# 카페24 카테고리 → 일본 컬렉션 핸들 (CLAUDE.md §12)
COLLECTION = {
    "브라": "bra", "누드브라": "bra",
    "팬티": "shorts",
    "캡나시": "inner", "FW": "inner",
    "스타킹": "leg",
}
ROLE_JA = {"pack": "セット", "color": "カラー", "size": "サイズ", "toe": "つま先"}
# 유발/무발 → 일본 유통 표기. 핸들은 ASCII 여야 하므로 슬러그도 함께 정한다.
TOE = {"유발": ("つま先あり", "toe"), "무발": ("つま先なし", "toeless")}


def jpy(krw):
    return int(round(krw / KRW_PER_100JPY * 100))


def handle_for(code, pno, suffix=""):
    h = f"{(code or 'p').lower()}-{pno}"
    return f"{h}-{suffix}" if suffix else h


def build():
    details = json.load(open(os.path.join(ROOT, "data", "details.json"), encoding="utf-8"))
    out, notes = [], collections.Counter()

    for d in details:
        sheet = d.get("_sheet") or {}
        cat = sheet.get("카테고리", "")
        variants = d.get("variants_simple") or []
        parsed = [(v, *split_options(v.get("options", ""))) for v in variants]
        axes = classify_axes([p for _, _, p in parsed if p])
        roles = [a["role"] for a in axes]

        krw = int(float(d.get("price") or 0))
        base = {
            "cafe24_product_no": d.get("product_no"),
            "cafe24_product_code": d.get("product_code"),
            "title_ko_source": d.get("product_name"),   # 번역 대기 — 그대로 둔다
            "price_jpy_placeholder": jpy(krw),
            "price_krw_source": krw,
            "collection_handle": COLLECTION.get(cat, ""),
            "status": "DRAFT",
            "vendor": "Marn5",
            "image": d.get("small_image"),
        }
        if not base["collection_handle"]:
            notes["컬렉션 미매핑"] += 1

        # ---- P0-1 : toe 축이 있으면 그 축으로 상품을 분리한다 ----
        split_idx = roles.index("toe") if "toe" in roles else None
        groups = collections.defaultdict(list)
        for v, _disc, parts in parsed:
            key = normalize_value(parts[split_idx]) if (
                split_idx is not None and split_idx < len(parts)) else ""
            groups[key].append((v, parts))
        if not groups:
            groups[""] = []          # 옵션이 없는 단일 상품도 반드시 내보낸다

        if split_idx is not None:
            notes["P0-1 분리된 상품"] += 1

        for gkey, members in groups.items():
            keep = [i for i in range(len(axes)) if i != split_idx]
            opt_names, opt_values = [], []
            for i in keep:
                vals = []
                for _v, parts in members:
                    if i < len(parts):
                        nv = normalize_value(parts[i])
                        if nv and nv not in vals:
                            vals.append(nv)
                if vals:
                    opt_names.append(ROLE_JA.get(roles[i], f"オプション{i+1}"))
                    opt_values.append(vals)

            vrows = []
            for v, parts in members:
                sel, neg = [], False
                for n, i in zip(opt_names, keep):
                    sel.append({"name": n,
                                "value": normalize_value(parts[i]) if i < len(parts) else ""})
                q = int(v.get("quantity") or 0)
                if q < 0:
                    neg = True
                    notes["음수 재고 클램프"] += 1
                vrows.append({
                    "sku": v.get("variant_code"),
                    "optionValues": sel,
                    "inventoryQuantity": max(0, q),      # P1-4
                    "negative_stock_source": q if neg else None,
                })

            if len(opt_names) > 3:
                notes["★3옵션 초과 (수동 확인)"] += 1

            ja_label, slug = TOE.get(gkey, (gkey, re.sub(r"[^a-z0-9]+", "", gkey.lower())[:12]))
            if gkey and not slug:
                notes["★분리 키 슬러그 없음 (수동 확인)"] += 1
            out.append({**base,
                        "handle": handle_for(d.get("product_code"), d.get("product_no"), slug),
                        "split_key": gkey,
                        "split_label_ja": ja_label if gkey else "",
                        "optionNames": opt_names,
                        "optionValues": opt_values,
                        "variants": vrows})

    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    path = os.path.join(ROOT, "out", "product_inputs.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"입력 상품 {len(details)} → 생성 상품 {len(out)}")
    print(f"variant 합계 {sum(len(p['variants']) for p in out)}")
    for k, c in notes.most_common():
        print(f"  {k}: {c}")
    print(f"\n→ {path}")
    print("\n주의: 전 상품 DRAFT. 가격은 환산 자리표시자이며 JPY 정가표가 아니다.")


if __name__ == "__main__":
    build()
