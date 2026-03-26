"""Load JSONL part files from the SAP O2C dataset folders."""

from pathlib import Path
from typing import Generator

import orjson


def load_jsonl_folder(folder_path: Path) -> list[dict]:
    """Read all .jsonl part files in a folder and return parsed records.

    Args:
        folder_path: Path to a dataset sub-folder (e.g. sales_order_headers/).

    Returns:
        List of dicts, one per JSON line across all part files.
    """
    records: list[dict] = []
    if not folder_path.exists():
        print(f"[WARN] Folder not found: {folder_path}")
        return records

    for part_file in sorted(folder_path.glob("*.jsonl")):
        for line in _iter_jsonl(part_file):
            records.append(line)

    print(
        f"[LOAD] {folder_path.name}: {len(records)} records from "
        f"{len(list(folder_path.glob('*.jsonl')))} file(s)"
    )
    return records


def iter_jsonl_folder(folder_path: Path) -> Generator[dict, None, None]:
    """Lazily yield records from all .jsonl files in a folder.

    Use this instead of load_jsonl_folder when memory is a concern.
    """
    if not folder_path.exists():
        print(f"[WARN] Folder not found: {folder_path}")
        return

    for part_file in sorted(folder_path.glob("*.jsonl")):
        yield from _iter_jsonl(part_file)


def _iter_jsonl(file_path: Path) -> Generator[dict, None, None]:
    """Parse a single JSONL file line by line using orjson."""
    with open(file_path, "rb") as f:
        for line_num, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                yield orjson.loads(raw_line)
            except orjson.JSONDecodeError as e:
                print(f"[ERR] {file_path.name}:{line_num} — {e}")


def load_all_folders(base_path: Path) -> dict[str, list[dict]]:
    """Load every dataset folder under the base path.

    Returns:
        Dict mapping folder name -> list of parsed records.
    """
    folder_names = [
        "sales_order_headers",
        "sales_order_items",
        "sales_order_schedule_lines",
        "outbound_delivery_headers",
        "outbound_delivery_items",
        "billing_document_headers",
        "billing_document_items",
        "billing_document_cancellations",
        "journal_entry_items_accounts_receivable",
        "payments_accounts_receivable",
        "business_partners",
        "business_partner_addresses",
        "customer_sales_area_assignments",
        "customer_company_assignments",
        "products",
        "product_descriptions",
        "product_plants",
        "product_storage_locations",
        "plants",
    ]

    data: dict[str, list[dict]] = {}
    for name in folder_names:
        data[name] = load_jsonl_folder(base_path / name)

    total = sum(len(v) for v in data.values())
    print(f"\n[LOAD] Total: {total} records across {len(data)} datasets")
    return data
