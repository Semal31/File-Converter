"""Data / spreadsheet format converter.

Supports: CSV, JSON, XLSX, XML, YAML, TSV
Engines: pandas, openpyxl, PyYAML, dicttoxml, lxml.
"""

import asyncio
import functools
import io
import json
import logging
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.data")

_EXTENSIONS: dict[str, list[str]] = {
    "csv": ["csv"],
    "json": ["json"],
    "xlsx": ["xlsx"],
    "xml": ["xml"],
    "yaml": ["yaml", "yml"],
    "tsv": ["tsv"],
}

_ALL = list(_EXTENSIONS.keys())


class DataConverter(BaseConverter):
    """Convert between tabular/structured data formats."""

    @property
    def supported_formats(self) -> list[str]:
        return _ALL

    def format_extensions(self, fmt: str) -> list[str]:
        return _EXTENSIONS.get(fmt, [])

    def get_output_formats(self, input_format: str) -> list[str]:
        return [f for f in _ALL if f != input_format]

    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        # quality kwarg is not applicable to data conversion; ignored.
        progress_callback = kwargs.get("progress_callback", None)
        fn = functools.partial(
            self._convert_sync, input_path, input_format, output_format, output_path,
            progress_callback=progress_callback,
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, fn)

    def _convert_sync(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        progress_callback=None,
        **kwargs,  # quality and other kwargs not applicable to this converter type
    ) -> None:
        # Load into a normalised Python object (list of dicts or a DataFrame)
        if progress_callback:
            progress_callback(50)
        data = self._load(input_path, input_format)
        self._save(data, output_format, output_path)
        if progress_callback:
            progress_callback(99)
        log.info("data: %s → %s OK", input_format, output_format)

    # ── Loaders ─────────────────────────────────────────────────────────────

    def _load(self, path: Path, fmt: str) -> object:
        import pandas as pd  # type: ignore
        import yaml  # type: ignore

        if fmt == "csv":
            return pd.read_csv(path)
        if fmt == "tsv":
            return pd.read_csv(path, sep="\t")
        if fmt == "xlsx":
            return pd.read_excel(path, engine="openpyxl")
        if fmt == "json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            # Normalise: wrap plain object in list so pandas works
            if isinstance(raw, dict):
                raw = [raw]
            if isinstance(raw, list):
                return pd.json_normalize(raw)
            raise ValueError("JSON root must be an object or array")
        if fmt == "xml":
            return pd.read_xml(path)
        if fmt == "yaml":
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = [raw]
            return pd.json_normalize(raw)
        raise ValueError(f"Unknown input data format: {fmt!r}")

    # ── Savers ──────────────────────────────────────────────────────────────

    def _save(self, data: object, fmt: str, path: Path) -> None:
        import pandas as pd  # type: ignore
        import yaml  # type: ignore

        # Ensure we have a DataFrame for tabular outputs
        if not isinstance(data, pd.DataFrame):
            df = pd.DataFrame(data)
        else:
            df = data

        if fmt == "csv":
            df.to_csv(path, index=False, encoding="utf-8")
        elif fmt == "tsv":
            df.to_csv(path, sep="\t", index=False, encoding="utf-8")
        elif fmt == "xlsx":
            df.to_excel(path, index=False, engine="openpyxl")
        elif fmt == "json":
            records = json.loads(df.to_json(orient="records", force_ascii=False))
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        elif fmt == "xml":
            self._df_to_xml(df, path)
        elif fmt == "yaml":
            records = json.loads(df.to_json(orient="records", force_ascii=False))
            path.write_text(yaml.dump(records, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        else:
            raise ValueError(f"Unknown output data format: {fmt!r}")

    @staticmethod
    def _df_to_xml(df, path: Path) -> None:  # type: ignore
        """Write DataFrame as well-formed XML with <root><row> structure."""
        import xml.etree.ElementTree as ET

        root = ET.Element("root")
        for _, row in df.iterrows():
            row_el = ET.SubElement(root, "row")
            for col, val in row.items():
                col_el = ET.SubElement(row_el, str(col).replace(" ", "_"))
                col_el.text = "" if val is None else str(val)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(path), encoding="unicode", xml_declaration=True)
