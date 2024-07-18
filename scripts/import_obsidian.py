#!/usr/bin/env python3
"""Obsidian 노트 폴더를 Hugo 페이지 번들로 복사한다. 원본 볼트는 읽기만 한다.

사용: import_obsidian.py <볼트> <content/blog> <폴더> [--until YYYY-MM-DD --span-days N]
- 노트 하나 = content/blog/<폴더 소문자>/<번호-제목>/index.md (+ 참조한 이미지)
- front matter가 없는 메모는 건너뛴다
- mermaid 코드 블록 -> {{< mermaid >}}, $$ 수식이 있으면 {{< katex >}} 추가 (Blowfish가 이 표시로 라이브러리를 불러옴)
- categories는 첫 항목만 남기고 나머지는 tags로, 같은 폴더 글은 series로 묶어 장 순서를 매김
- --until을 주면 그 날 전 N일 안에서 저녁 시각으로 무작위 날짜를 붙이고, 장 순서대로 커지게 정렬 (폴더 이름을 시드로 써서 다시 돌려도 같음)
"""
import argparse, datetime as dt, random, re, shutil, sys
from pathlib import Path
import yaml

FENCE = re.compile(r"^(\x60{3,}|~{3,})(.*)$")
IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")

def split_front_matter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end]), text[end + 5:]

def convert_body(body):
    out, fence, is_mermaid, has_math = [], None, False, False
    for line in body.split("\n"):
        m = FENCE.match(line.strip())
        if fence is None and m:
            fence, is_mermaid = m.group(1), m.group(2).strip() == "mermaid"
            out.append("{{< mermaid >}}" if is_mermaid else line)
        elif fence is not None and line.strip() == fence:
            out.append("{{< /mermaid >}}" if is_mermaid else line)
            fence = None
        else:
            if fence is None and "$$" in line:
                has_math = True
            out.append(line)
    assert fence is None, "닫히지 않은 코드 블록"
    body = "\n".join(out)
    return ("{{< katex >}}\n" + body) if has_math else body

def random_dates(n, until, span_days, seed):
    rng = random.Random(seed)
    kst = dt.timezone(dt.timedelta(hours=9))
    first = until - dt.timedelta(days=span_days)
    out = []
    for _ in range(n):
        day = first + dt.timedelta(days=rng.randrange(span_days))
        out.append(dt.datetime(day.year, day.month, day.day, rng.randint(19, 23), rng.randrange(60), tzinfo=kst))
    return sorted(out)

def slug(path):
    parts = [p.split(" ", 1) for p in path.with_suffix("").parts]
    nums = [p[0] for p in parts if p[0].isdigit()]
    name = parts[-1][-1]
    name = re.sub(r"[^\w가-힣]+", "-", name).strip("-").lower()
    return "-".join(nums + [name])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault"); ap.add_argument("dest"); ap.add_argument("folder")
    ap.add_argument("--until", type=dt.date.fromisoformat)
    ap.add_argument("--span-days", type=int, default=42)
    a = ap.parse_args()
    root = Path(a.vault) / a.folder
    notes = []
    for p in sorted(root.rglob("*.md")):
        if p.name.startswith("._"):
            continue
        if not p.read_text(encoding="utf-8").startswith("---\n"):
            print("건너뜀(front matter 없음):", p.relative_to(root)); continue
        notes.append(p)
    series = a.folder
    out_root = Path(a.dest) / a.folder.lower().replace(" ", "-")  # "AWS SAA" -> aws-saa (URL에 공백이 들어가지 않게)
    if out_root.exists():
        shutil.rmtree(out_root)  # 다시 돌려도 같은 결과가 나오게 이 폴더만 새로 만듦
    dates = None
    if a.until:
        dates = random_dates(len(notes), a.until, a.span_days, a.folder)
    order = 0
    for note in notes:
        fm, body = split_front_matter(note.read_text(encoding="utf-8"))
        order += 1
        cats = list(fm.get("categories") or [series])
        fm["categories"] = cats[:1]
        fm["tags"] = list(fm.get("tags") or []) + [c for c in cats[1:] if c not in (fm.get("tags") or [])]
        fm["series"] = [series]; fm["series_order"] = order
        fm.pop("mermaid", None)
        when = fm.get("date")
        when = when if isinstance(when, dt.datetime) else dt.datetime.strptime(str(when), "%Y-%m-%d %H:%M:%S %z")
        if dates:
            when = dates[order - 1]
        fm["date"] = when.isoformat()
        bundle = out_root / slug(note.relative_to(root))
        bundle.mkdir(parents=True)
        for ref in IMG.findall(body):
            if re.match(r"^[a-z]+://", ref):
                continue
            src = (note.parent / ref).resolve()
            assert src.is_file(), f"이미지 없음: {note} -> {ref}"
            dst = (bundle / ref).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        body = convert_body(body)
        assert "![[" not in body, f"Obsidian 이미지 문법 남음: {note}"
        fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=1000)
        (bundle / "index.md").write_text(f"---\n{fm_text}---\n{body}", encoding="utf-8")
    print(f"{a.folder}: {order}편 -> {out_root}")

if __name__ == "__main__":
    # 자체 점검: 머메이드 변환, 수식 표시, 코드 안의 $$는 무시
    t = convert_body("a\n\x60\x60\x60mermaid\ngraph LR\n\x60\x60\x60\n\x60\x60\x60r\nx$$y\n\x60\x60\x60\n")
    assert "{{< mermaid >}}\ngraph LR\n{{< /mermaid >}}" in t and not t.startswith("{{< katex"), t
    assert convert_body("$$\nx\n$$").startswith("{{< katex >}}")
    assert slug(Path("03 데이터 분석/02 통계 분석/01 표본추출, 척도, 확률분포.md")) == "03-02-01-표본추출-척도-확률분포"
    ds = random_dates(31, dt.date(2025, 3, 8), 49, "SQLD")
    assert ds == sorted(ds) and ds[0].date() >= dt.date(2025, 1, 18) and ds[-1].date() < dt.date(2025, 3, 8), ds
    assert ds == random_dates(31, dt.date(2025, 3, 8), 49, "SQLD")
    main()

