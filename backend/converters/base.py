"""Abstract base class for all format converters."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseConverter(ABC):
    """Interface every converter module must implement."""

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Canonical format identifiers handled by this converter (e.g. ['pdf', 'docx'])."""
        ...

    @abstractmethod
    def format_extensions(self, fmt: str) -> list[str]:
        """File extensions (without dot) that map to *fmt* (e.g. ['jpg', 'jpeg'])."""
        ...

    @abstractmethod
    def get_output_formats(self, input_format: str) -> list[str]:
        """Return valid output format identifiers for a given input format."""
        ...

    @abstractmethod
    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        """Perform the conversion, writing result to *output_path*.

        Kwargs are converter-specific and silently ignored by converters that
        don't use them. Currently recognised kwargs:
            quality (str): "original" | "high" | "medium" | "low"
        """
        ...
