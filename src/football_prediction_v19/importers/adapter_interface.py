# -*- coding: utf-8 -*-
"""Preview-only importer adapter interface contracts.

The base adapter does not perform network calls. Future provider adapters must
explicitly implement fetching and normalization in a later phase.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY = "IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY"
IMPORTER_ADAPTER_NETWORK_DISABLED_BY_DESIGN = "IMPORTER_ADAPTER_NETWORK_DISABLED_BY_DESIGN"
IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED = "IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED"
IMPORTER_ADAPTER_CONFIG_INVALID = "IMPORTER_ADAPTER_CONFIG_INVALID"
IMPORTER_ADAPTER_NOT_IMPLEMENTED = "IMPORTER_ADAPTER_NOT_IMPLEMENTED"


@dataclass(frozen=True)
class ImporterAdapterConfig:
    source_id: str
    provider_name: str
    supported_contracts: tuple[str, ...] = field(default_factory=tuple)
    network_enabled: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImporterRunContext:
    requested_contracts: tuple[str, ...] = field(default_factory=tuple)
    preview_only: bool = True
    allow_network: bool = False
    notes: str = ""


@dataclass(frozen=True)
class ImporterAdapterResult:
    source_id: str
    provider_name: str
    adapter_status: str
    network_calls_enabled: bool
    contracts_supported: tuple[str, ...]
    rows_normalized: int
    recommendation: str
    notes: str = ""


class BaseImporterAdapter(ABC):
    """Base contract for future importer adapters."""

    def __init__(self, config: ImporterAdapterConfig) -> None:
        self.config = config

    @property
    def source_id(self) -> str:
        return self.config.source_id

    @property
    def provider_name(self) -> str:
        return self.config.provider_name

    @property
    def network_enabled(self) -> bool:
        return bool(self.config.network_enabled)

    @property
    def supported_contracts(self) -> tuple[str, ...]:
        return tuple(self.config.supported_contracts)

    def validate_config(self) -> tuple[bool, str]:
        if not str(self.source_id).strip():
            return False, "SOURCE_ID_REQUIRED"
        if not str(self.provider_name).strip():
            return False, "PROVIDER_NAME_REQUIRED"
        if self.network_enabled:
            return False, "NETWORK_DISABLED_BY_DESIGN"
        if not self.supported_contracts:
            return False, "SUPPORTED_CONTRACTS_REQUIRED"
        return True, "CONFIG_VALID"

    def validate_contract_support(self, requested_contracts: tuple[str, ...] | None = None) -> tuple[bool, str]:
        requested = tuple(requested_contracts or self.supported_contracts)
        missing = [contract for contract in requested if contract not in self.supported_contracts]
        if missing:
            return False, "UNSUPPORTED_CONTRACTS:" + ",".join(missing)
        return True, "CONTRACT_SUPPORT_VALID"

    @abstractmethod
    def fetch_raw(self, context: ImporterRunContext) -> Any:
        raise NotImplementedError(IMPORTER_ADAPTER_NOT_IMPLEMENTED)

    @abstractmethod
    def normalize(self, raw: Any, context: ImporterRunContext) -> Any:
        raise NotImplementedError(IMPORTER_ADAPTER_NOT_IMPLEMENTED)

    def run_preview(self, context: ImporterRunContext | None = None) -> ImporterAdapterResult:
        context = context or ImporterRunContext(requested_contracts=self.supported_contracts)
        config_ok, config_note = self.validate_config()
        if not config_ok:
            return ImporterAdapterResult(
                source_id=self.source_id,
                provider_name=self.provider_name,
                adapter_status=IMPORTER_ADAPTER_CONFIG_INVALID,
                network_calls_enabled=False,
                contracts_supported=self.supported_contracts,
                rows_normalized=0,
                recommendation=IMPORTER_ADAPTER_CONFIG_INVALID,
                notes=config_note,
            )
        contract_ok, contract_note = self.validate_contract_support(context.requested_contracts)
        if not contract_ok:
            return ImporterAdapterResult(
                source_id=self.source_id,
                provider_name=self.provider_name,
                adapter_status=IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED,
                network_calls_enabled=False,
                contracts_supported=self.supported_contracts,
                rows_normalized=0,
                recommendation=IMPORTER_ADAPTER_CONTRACT_VALIDATION_FAILED,
                notes=contract_note,
            )
        return ImporterAdapterResult(
            source_id=self.source_id,
            provider_name=self.provider_name,
            adapter_status=IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
            network_calls_enabled=False,
            contracts_supported=self.supported_contracts,
            rows_normalized=0,
            recommendation=IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
            notes=f"{IMPORTER_ADAPTER_NETWORK_DISABLED_BY_DESIGN}; preview validates config and contracts only.",
        )
