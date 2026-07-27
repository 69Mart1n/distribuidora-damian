"""Extrae la lista mayorista validada a los artefactos de carga inicial."""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pdfplumber


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("—", "").strip())


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return re.sub(r"[^a-z0-9]+", "-", normalized.encode("ascii", "ignore").decode().lower()).strip("-")


def category_for(supplier: str, name: str, presentation: str) -> str:
    text = f"{supplier} {name} {presentation}".lower()
    if any(word in text for word in ("collar", "oreja", "hueso", "snak", "palito")):
        return "Accesorios"
    if any(word in text for word in ("nexgard", "simparica", "pipeta", "antiparasitario")):
        return "Antiparasitarios"
    if any(word in text for word in ("semilla", "maíz", "maiz", "arroz", "alpiste", "polenta", "afrechillo", "semitin")):
        return "Semillas"
    if any(word in text for word in ("cerdo", "ovino", "equino", "esquino", "conejo", "ponedora", "engorde", "iniciador")):
        return "Animales de granja"
    if any(word in text for word in ("gato", "cat", "whiskas", "felix", "gatito", "gati")):
        return "Gatos"
    if any(word in text for word in ("perro", "dog", "can", "cachorro", "adulto", "puppy")):
        return "Perros"
    return "Otros"


def parse_price(raw: str) -> int | None:
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def extract(pdf_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    products: list[dict[str, object]] = []
    promotions: list[dict[str, object]] = []
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                continue
            rows = tables[0]
            if page_number == 2:
                for row in rows[1:]:
                    name, threshold, discount = (clean(cell) for cell in row[:3])
                    match = re.search(r"([\d,]+)%", discount)
                    promotions.append(
                        {
                            "name": name,
                            "minimumKg": float(threshold.lower().replace("kg", "").replace(",", ".").strip()),
                            "discountPercentage": float(match.group(1).replace(",", ".")) if match else 0,
                        }
                    )
                continue

            supplier = next(
                (clean(cell) for cell in rows[0] if clean(cell)),
                f"Página {page_number}",
            )
            header_index = -1
            code = 1
            for row in rows:
                cells = [clean(cell) for cell in row]
                if not cells or not cells[0]:
                    continue
                if cells[0].lower() == "producto":
                    header_index += 1
                    continue
                if header_index < 0:
                    continue

                if page_number == 20 and header_index == 1:
                    name, size, pack, price_raw = cells[:4]
                    presentation = clean(f"{size} · {pack}")
                else:
                    name = cells[0]
                    presentation = cells[1] if len(cells) > 1 else "Unidad"
                    price_raw = cells[2] if len(cells) > 2 else ""
                if not name:
                    continue
                products.append(
                    {
                        "id": f"pdf-{page_number:02d}-{code:03d}",
                        "code": f"P{len(products) + 1:04d}",
                        "name": name,
                        "presentation": presentation or "Unidad",
                        "supplier": supplier,
                        "category": category_for(supplier, name, presentation),
                        "wholesalePrice": parse_price(price_raw),
                        "active": True,
                        "requiresReview": parse_price(price_raw) is None,
                        "sourcePage": page_number,
                    }
                )
                code += 1

    duplicates = Counter(
        (str(row["supplier"]).casefold(), str(row["name"]).casefold(), str(row["presentation"]).casefold())
        for row in products
    )
    deduplicated: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in products:
        key = (
            str(row["supplier"]).casefold(),
            str(row["name"]).casefold(),
            str(row["presentation"]).casefold(),
        )
        if duplicates[key] > 1:
            row["requiresReview"] = True
            prices = sorted(
                {
                    int(candidate["wholesalePrice"])
                    for candidate in products
                    if (
                        str(candidate["supplier"]).casefold(),
                        str(candidate["name"]).casefold(),
                        str(candidate["presentation"]).casefold(),
                    )
                    == key
                    and candidate["wholesalePrice"] is not None
                }
            )
            row["wholesalePrice"] = None
            row["reviewNote"] = "Precios conflictivos en el PDF: " + ", ".join(f"${price}" for price in prices)
            if key in seen:
                continue
        seen.add(key)
        row.setdefault("reviewNote", "")
        deduplicated.append(row)
    for index, row in enumerate(deduplicated, start=1):
        row["code"] = f"P{index:04d}"
    return deduplicated, promotions


def sql_quote(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Uso: extract_prices.py <lista.pdf> <directorio-salida>")
    pdf_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    products, promotions = extract(pdf_path)

    (output_dir / "products.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "promotions.json").write_text(
        json.dumps(promotions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "products.csv").open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=products[0].keys())
        writer.writeheader()
        writer.writerows(products)

    values = []
    for product in products:
        values.append(
            "("
            + ", ".join(
                sql_quote(product[key])
                for key in (
                    "code",
                    "name",
                    "presentation",
                    "supplier",
                    "category",
                    "wholesalePrice",
                    "active",
                    "requiresReview",
                    "sourcePage",
                    "reviewNote",
                )
            )
            + ")"
        )
    seed_sql = (
        "-- Generado desde Precios Por Mayor.pdf. Los conflictos conservan la fila más reciente.\n"
        "insert into public.products "
        "(code, name, presentation, supplier, category, wholesale_price, active, requires_review, source_page, notes)\nvalues\n"
        + ",\n".join(values)
        + "\non conflict (supplier, name, presentation) do update set\n"
        "  wholesale_price = excluded.wholesale_price,\n"
        "  category = excluded.category,\n"
        "  requires_review = excluded.requires_review,\n"
        "  source_page = excluded.source_page,\n"
        "  notes = excluded.notes,\n"
        "  updated_at = now();\n"
    )
    (output_dir / "seed_products.sql").write_text(seed_sql, encoding="utf-8")
    print(
        json.dumps(
            {
                "products": len(products),
                "priced": sum(row["wholesalePrice"] is not None for row in products),
                "review": sum(bool(row["requiresReview"]) for row in products),
                "promotions": len(promotions),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
