import csv
import argparse
from pathlib import Path

SOURCE_FILES = [
    "产品服务_TICKET_ACTIVITY_门票活动.csv",
    "产品服务_GUIDE_导游.csv",
    "产品服务_OTHER_其他.csv",
    "产品服务_TRANS_车辆.csv",
]


def normalize_row(row, header):
    # 保证每行有相同字段（列）
    return {k: row.get(k, "") for k in header}


def load_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def merge_city(city, sources, out_path):
    all_rows = []
    all_headers = []

    for p in sources:
        if not p.exists():
            raise FileNotFoundError(f"文件不存在: {p}")

    for src in sources:
        headers, rows = load_csv(src)
        if headers is None:
            headers = []
        if not all_headers:
            all_headers = headers.copy()
        else:
            for h in headers:
                if h not in all_headers:
                    all_headers.append(h)

        for r in rows:
            if r.get("城市", "").strip() == city:
                all_rows.append(normalize_row(r, all_headers))

    # 如果在循环里添加新 header，所有已选行需要更新一遍
    all_rows = [normalize_row(r, all_headers) for r in all_rows]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fw:
        writer = csv.DictWriter(fw, fieldnames=all_headers)
        writer.writeheader()
        writer.writerows(all_rows)

    return len(all_rows)


def main():
    parser = argparse.ArgumentParser(description="按城市合并产品服务 CSV")
    parser.add_argument("--city", required=True, help="目标城市名称，例如：北京")
    parser.add_argument("--src-dir", default=".", help="CSV 文件所在目录，默认当前目录")
    parser.add_argument("--out", default=None, help="输出文件路径，默认 mashes/{city}_merged.csv")
    args = parser.parse_args()

    base = Path(args.src_dir)
    sources = [base / fn for fn in SOURCE_FILES]
    out_file = Path(args.out or f"mashes/{args.city}_merged.csv")

    count = merge_city(args.city, sources, out_file)
    print(f"已输出 {count} 行到 {out_file}（含表头）")


if __name__ == "__main__":
    main()
