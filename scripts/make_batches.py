#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
out/product_inputs.json → productSet 배치 변수 (out/batch_NN.json)
================================================================
MCP graphql_mutation 에 그대로 붙여 넣을 수 있는 형태로 만든다.

관세 구분(`custom.duty_exempt_class`)은 CLAUDE.md §5 의 **추정값**이다.
통관사 확정 전이므로 값에 「推定」을 붙여 둔다. 그대로 게시하지 말 것.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCATION = "gid://shopify/Location/87807557786"
COLL = {
    "bra": "gid://shopify/Collection/367103508634",
    "shorts": "gid://shopify/Collection/367103541402",
    "inner": "gid://shopify/Collection/367103574170",
    "leg": "gid://shopify/Collection/367103606938",
    "homewear": "gid://shopify/Collection/367103639706",
}
BATCH = 5

# 카페24 카테고리 → 1만엔 면세 판정 (CLAUDE.md §5) · 전부 추정
DUTY = {
    "브라": "推定: 免税可 (HS 6212)",
    "누드브라": "推定: 免税可 (HS 3926.20 / 6212 · 分類確認要)",
    "팬티": "推定: 課税 (HS 6108)",
    "캡나시": "推定: 課税 (HS 6109 / 6114)",
    "FW": "推定: 課税 (HS 6109 / 6110)",
}
# 레그는 품목이 갈린다 — 팬티스타킹/타이츠는 과세, 일반 양말·레그워머는 면세 가능
LEG_TAXED = "推定: 課税 (HS 6115.21〜29 パンティストッキング・タイツ)"
LEG_FREE = "推定: 免税可 (HS 6115.9x / 6117 一般靴下・レッグウォーマー)"


def duty_class(cat, name):
    if cat in DUTY:
        return DUTY[cat]
    if cat == "스타킹":
        n = name or ""
        if any(k in n for k in ("팬티스타킹", "타이츠", "스타킹")) and \
           not any(k in n for k in ("삭스", "양말", "레그워머", "니삭스")):
            return LEG_TAXED
        return LEG_FREE
    return "推定: 未分類 — 通関業者の確定待ち"


def main():
    src = json.load(open(os.path.join(ROOT, "out", "product_inputs.json"), encoding="utf-8"))
    by_no = {}
    for d in json.load(open(os.path.join(ROOT, "data", "details.json"), encoding="utf-8")):
        by_no[d["product_no"]] = (d.get("_sheet") or {}).get("카테고리", "")

    products = []
    for p in src:
        cat = by_no.get(p["cafe24_product_no"], "")
        title = p["title_ko_source"]
        if p.get("split_label_ja"):
            title = f"{title}（{p['split_label_ja']}）"

        # Shopify 는 같은 상품 안에서 옵션명 중복을 허용하지 않는다.
        # 축 역할이 겹치는 상품이 있다 (pack×color×color 등) → 뒤에 번호를 붙인다.
        names, seen = [], {}
        for n in p["optionNames"]:
            seen[n] = seen.get(n, 0) + 1
            names.append(n if seen[n] == 1 else f"{n} {seen[n]}")
        opts = [{"name": n, "values": [{"name": v} for v in vals]}
                for n, vals in zip(names, p["optionValues"])]

        variants = []
        for v in p["variants"]:
            variants.append({
                "optionValues": [{"optionName": names[i], "name": s["value"]}
                                 for i, s in enumerate(v["optionValues"])],
                "price": str(p["price_jpy_placeholder"]),
                "sku": v["sku"],
                "inventoryItem": {"tracked": True},
            })
            # 재고 0 은 기본값이므로 payload 에서 뺀다 (183건 중 180건이 0)
            if v["inventoryQuantity"]:
                variants[-1]["inventoryQuantities"] = [
                    {"locationId": LOCATION, "name": "available",
                     "quantity": v["inventoryQuantity"]}]
        if not variants:
            # 옵션 없는 단일 상품. productSet 은 옵션 없이 variant 를 못 만든다
            # (PRODUCT_OPTIONS_INPUT_MISSING) → Shopify 기본 옵션을 명시한다.
            opts = [{"name": "Title", "values": [{"name": "Default Title"}]}]
            variants = [{
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": str(p["price_jpy_placeholder"]),
                "sku": p["cafe24_product_code"],
                "inventoryItem": {"tracked": True},
            }]

        item = {
            "handle": p["handle"],
            "title": title,
            "status": "DRAFT",
            "vendor": "Marn5",
            "productType": cat,
            "descriptionHtml": (
                "<p><strong>⚠ 下書き — 日本語コピー未作成。</strong>"
                "商品名は韓国語原文のまま。無監修の自動翻訳は行っていない。</p>"
                "<p>素材組成・取扱い表示・原産地・実測サイズは原資料が未確保のため空欄。</p>"),
            "metafields": [{
                "namespace": "custom", "key": "duty_exempt_class",
                "value": duty_class(cat, p["title_ko_source"]),
                "type": "single_line_text_field",
            }],
            "variants": variants,
        }
        if opts:
            item["productOptions"] = opts
        if p.get("collection_handle") in COLL:
            item["collections"] = [COLL[p["collection_handle"]]]
        if p.get("image"):
            item["files"] = [{"originalSource": p["image"], "contentType": "IMAGE",
                              "alt": p["title_ko_source"]}]
        products.append(item)

    out_dir = os.path.join(ROOT, "out")
    n = 0
    for i in range(0, len(products), BATCH):
        chunk = products[i:i + BATCH]
        n += 1
        variables = {f"p{j+1}": c for j, c in enumerate(chunk)}
        json.dump(variables, open(f"{out_dir}/batch_{n:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False)
        print(f"batch_{n:02d}.json  상품 {len(chunk)}  variant {sum(len(c['variants']) for c in chunk)}")
    print(f"\n총 {len(products)}상품 / {n}배치 · 전부 DRAFT")


if __name__ == "__main__":
    main()
