from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)

INTEGER_FIELDS = {
    "smr_version",
    "voltage_sag_l1_count",
    "voltage_sag_l2_count",
    "voltage_sag_l3_count",
    "voltage_swell_l1_count",
    "voltage_swell_l2_count",
    "voltage_swell_l3_count",
    "any_power_fail_count",
    "long_power_fail_count",
}

DERIVED_SOURCE_FIELDS = {
    "active_power_import_w",
    "active_power_export_w",
    "active_power_import_l1_w",
    "active_power_export_l1_w",
    "active_power_import_l2_w",
    "active_power_export_l2_w",
    "active_power_import_l3_w",
    "active_power_export_l3_w",
}


@dataclass(frozen=True)
class SensorMapping:
    field: str
    entity_id: str
    attribute: str | None = None
    scale: float = 1.0
    offset: float = 0.0


class MeasurementCache:
    def __init__(self, mappings: dict[str, Any]) -> None:
        self._mappings: tuple[SensorMapping, ...] = tuple()
        self._by_entity: dict[str, list[SensorMapping]] = {}
        self._values: dict[str, int | float] = {}
        self.set_mappings(mappings)

    def set_mappings(self, mappings: dict[str, Any]) -> None:
        self._mappings = tuple(self._parse_mapping(field, value) for field, value in mappings.items())
        self._by_entity = {}
        for mapping in self._mappings:
            self._by_entity.setdefault(mapping.entity_id, []).append(mapping)
        self._values = {}

    @staticmethod
    def _parse_mapping(field: str, value: Any) -> SensorMapping:
        if isinstance(value, str):
            return SensorMapping(field=field, entity_id=value.strip())
        if not isinstance(value, dict) or not value.get("entity_id"):
            raise ValueError(f"sensor mapping for {field} must have an entity_id")
        return SensorMapping(
            field=field,
            entity_id=str(value["entity_id"]).strip(),
            attribute=value.get("attribute"),
            scale=float(value.get("scale", 1)),
            offset=float(value.get("offset", 0)),
        )

    @property
    def entity_ids(self) -> frozenset[str]:
        return frozenset(self._by_entity)

    def update_state(self, state: dict[str, Any]) -> bool:
        entity_id = state.get("entity_id")
        mappings = self._by_entity.get(entity_id, ())
        updated = False
        for mapping in mappings:
            raw_value = state.get("state")
            if mapping.attribute:
                raw_value = state.get("attributes", {}).get(mapping.attribute)
            try:
                numeric_value = float(raw_value)
                unit = state.get("attributes", {}).get("unit_of_measurement")
                converted = self._convert_unit(mapping.field, numeric_value, unit)
                converted = converted * mapping.scale + mapping.offset
                if mapping.field in INTEGER_FIELDS:
                    converted = int(converted)
                self._values[mapping.field] = converted
                updated = True
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Ignoring non-numeric state for %s from %s: %r",
                    mapping.field,
                    entity_id,
                    raw_value,
                )
        return updated

    @staticmethod
    def _convert_unit(field: str, value: float, unit: str | None) -> float:
        normalized = (unit or "").strip().lower().replace("³", "3")
        if field.endswith("_w") and normalized == "kw":
            return value * 1000
        if field.endswith("_kwh") and normalized == "wh":
            return value / 1000
        if field.endswith("_kwh") and normalized == "mwh":
            return value * 1000
        if field.endswith("_m3") and normalized in {"l", "liter", "litre"}:
            return value / 1000
        if field.endswith("_a") and normalized == "ma":
            return value / 1000
        if field.endswith("_v") and normalized == "mv":
            return value / 1000
        return value

    def snapshot(self) -> dict[str, int | float]:
        result = {
            field: value
            for field, value in self._values.items()
            if field not in DERIVED_SOURCE_FIELDS
        }
        if "active_power_w" not in result:
            self._derive_net_power(result, "active_power_w", "active_power_import_w", "active_power_export_w")
        for phase in range(1, 4):
            self._derive_net_power(
                result,
                f"active_power_l{phase}_w",
                f"active_power_import_l{phase}_w",
                f"active_power_export_l{phase}_w",
            )
        self._derive_tariff_total(result, "total_power_import")
        self._derive_tariff_total(result, "total_power_export")
        return result

    def _derive_net_power(
        self,
        result: dict[str, int | float],
        target: str,
        import_source: str,
        export_source: str,
    ) -> None:
        if target in result:
            return
        imported = self._values.get(import_source)
        exported = self._values.get(export_source)
        if imported is not None or exported is not None:
            result[target] = (imported or 0) - (exported or 0)

    @staticmethod
    def _derive_tariff_total(result: dict[str, int | float], prefix: str) -> None:
        total_field = f"{prefix}_kwh"
        if total_field in result:
            return
        tariffs = [
            result[field]
            for number in range(1, 5)
            if (field := f"{prefix}_t{number}_kwh") in result
        ]
        if tariffs:
            result[total_field] = sum(tariffs)
