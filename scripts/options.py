#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카페24 옵션 문자열 파서 · 정규화 · 축 역할 판정
================================================

카페24는 옵션 조합을 **하이픈으로 이어붙인 단일 문자열**로만 노출한다.
축 구분자도 하이픈이고, 값 안에도 하이픈이 들어간다. 둘을 구분해야 한다.

    '[10%] 4매입-블랙 2매+ 아이보리 2매-F/L (44-66)'
                ^축              ^축         ^값 내부(범위)

순진하게 split("-") 하면 축이 3개가 아니라 4개로 잡힌다.
실제로 이 오류 때문에 P0-1(4축 상품) 건수가 과다 계상돼 있었다.

보호 규칙
---------
R1  괄호 `( )` 안의 하이픈은 구분자가 아니다.       'F/L (44-66)' · 'M(남성 95-100/여성77-88)'
R2  사이즈 토큰끼리 맞닿은 하이픈은 범위 표기다.     'S-M'  → 한 개 값

정규화 규칙
-----------
N1  연속 공백을 하나로
N2  여는 괄호 앞 공백을 제거          'F/L (44-66)' ≡ 'F/L(44-66)'
    → 같은 사이즈가 Shopify 옵션값 2개로 갈라지는 것을 막는다

주의: Catalog MCP 는 상품당 variant 를 **최대 5건**만 반환한다.
      여기서 얻는 축 구성은 실제 조합의 하한이며, 앞 5건에 등장하지 않은
      축은 통째로 보이지 않는다. Admin API 전량 추출 후 재판정할 것.

표준 라이브러리만 사용한다.
"""

import re

__all__ = [
    "split_options", "normalize_value", "axis_role",
    "classify_axes", "SIZE_TOKENS",
]

# 단독으로 쓰이면 사이즈로 보는 토큰 (R2 · 역할 판정 공용)
SIZE_TOKENS = {
    "XS", "S", "M", "L", "XL", "XXL", "XXXL", "2XL", "3XL", "4XL",
    "FREE", "F", "F/L", "M/L", "S/M", "L/XL",
}

_DISCOUNT = re.compile(r"^\s*(\[[^\]]*\])\s*")
_SIZE_ONLY = re.compile(r"^(?:" + "|".join(
    re.escape(t) for t in sorted(SIZE_TOKENS, key=len, reverse=True)) + r")$")

# 역할 판정용
_RE_PACK = re.compile(r"(\d+\s*매입|\d+\s*세트|\d+\s*팩|단품|매입|세트만)")
_RE_TOE = re.compile(r"^(유발|무발)$")
_SZ = (r"(?:XS|S|M|L|XL|XXL|XXXL|[234]XL|FREE|F|[A-G]|"      # 알파벳 사이즈 · 컵
       r"F/L|M/L|S/M|L/XL)")                                 # 슬래시 범위형
_RE_SIZEISH = re.compile(
    rf"^{_SZ}(-{_SZ})?"                                       # 'S' · 'S-M'(하이픈 범위)
    r"(\s*\(.*\))?$"                                          # 'XL (66-88)' 꼬리 허용
)


def _protect(opt: str):
    """R1·R2 로 보호할 하이픈을 \x00 으로 치환해 split 대상에서 뺀다."""
    out, depth = [], 0
    for ch in opt:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        out.append("\x00" if (ch == "-" and depth > 0) else ch)   # R1
    s = "".join(out)

    # R2 — 사이즈 토큰 사이의 하이픈
    def _range(m):
        return f"{m.group(1)}\x00{m.group(2)}"

    alt = "|".join(re.escape(t) for t in sorted(SIZE_TOKENS, key=len, reverse=True))
    s = re.sub(rf"(?<![^\-\x00\s])({alt})-({alt})(?![^\-\x00\s])", _range, s)
    return s


def split_options(opt: str):
    """옵션 원문 → (할인표기, [축값…])

    >>> split_options('[10%] 4매입-블랙 2매+ 아이보리 2매-F/L (44-66)')
    ('[10%]', ['4매입', '블랙 2매+ 아이보리 2매', 'F/L (44-66)'])
    >>> split_options('[10%] 4매입-내추럴 4매-S-M')
    ('[10%]', ['4매입', '내추럴 4매', 'S-M'])
    """
    if not opt:
        return "", []
    disc = ""
    m = _DISCOUNT.match(opt)
    if m:
        disc = m.group(1)
        opt = opt[m.end():]
    parts = _protect(opt).split("-")
    return disc, [p.replace("\x00", "-").strip() for p in parts if p.strip()]


def normalize_value(v: str) -> str:
    """N1·N2 — 표기 흔들림 흡수. 'F/L (44-66)' → 'F/L(44-66)'"""
    if not v:
        return ""
    v = re.sub(r"\s+", " ", v).strip()
    v = re.sub(r"\s+\(", "(", v)
    return v


def axis_role(values) -> str:
    """축에 실린 값들을 보고 역할을 판정한다.

    카페24는 축 순서를 강제하지 않아 상품마다 배치가 다르다.
    a1=수량 / a2=컬러 / a3=사이즈 식의 **위치 기반 매핑은 깨진다**
    (MVP 41건 중 4건에서 a3 이 사이즈가 아니다).
    """
    vals = [normalize_value(v) for v in values if v]
    if not vals:
        return "unknown"
    if all(_RE_TOE.match(v) for v in vals):
        return "toe"          # 유발/무발 → Shopify 에서는 별도 상품 분리 권장
    if all(_RE_PACK.search(v) for v in vals):
        return "pack"         # 수량구성
    if all(_RE_SIZEISH.match(v) for v in vals):
        return "size"
    return "color"            # 나머지는 컬러/구성 (합본·세트 표기 포함)


def classify_axes(variant_parts):
    """상품 단위. [[축값…], …] → [{'index','role','values'}…]"""
    if not variant_parts:
        return []
    width = max(len(p) for p in variant_parts)
    axes = []
    for i in range(width):
        vals = []
        for parts in variant_parts:
            if i < len(parts):
                v = normalize_value(parts[i])
                if v and v not in vals:
                    vals.append(v)
        axes.append({"index": i, "role": axis_role(vals), "values": vals})
    return axes


if __name__ == "__main__":
    import doctest
    fail, run = doctest.testmod()
    print(f"doctest {run - fail}/{run} 통과")
