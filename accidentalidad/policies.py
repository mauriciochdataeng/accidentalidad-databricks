"""Políticas independientes de Spark para validar configuración y decisiones."""

import math
import re


def sql_identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador SQL inválido: {value!r}")
    return value


def parse_bool(value):
    if value not in ("true", "false"):
        raise ValueError("Se esperaba true o false")
    return value == "true"


def nonnegative_int(value):
    result = int(value)
    if result < 0:
        raise ValueError("Se esperaba un entero no negativo")
    return result


def temporal_partition(year, start=2018, validation=2021, test=2022):
    if not start < validation < test:
        raise ValueError("Los límites temporales deben ser crecientes")
    if year is None:
        return "excluded"
    if start <= year < validation:
        return "train"
    if year == validation:
        return "validation"
    if year == test:
        return "test"
    return "excluded"


def choose_candidate(results):
    if not results:
        raise ValueError("No hay candidatos")
    for row in results:
        if not math.isfinite(row["validation_f1"]) or not 0 <= row["validation_f1"] <= 1:
            raise ValueError("F1 de validación inválido")
    return sorted(results, key=lambda row: (-row["validation_f1"], row["model"]))[0]


def promotion_allowed(candidate_f1, baseline_f1, champion_f1=None, minimum=0.5, improvement=0.0):
    values = [candidate_f1, baseline_f1, minimum]
    if champion_f1 is not None:
        values.append(champion_f1)
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values):
        raise ValueError("Las métricas y el umbral deben estar entre 0 y 1")
    if not math.isfinite(improvement) or not 0 <= improvement <= 1:
        raise ValueError("La mejora mínima debe estar entre 0 y 1")
    return (
        candidate_f1 >= minimum
        and candidate_f1 > baseline_f1
        and (champion_f1 is None or candidate_f1 > champion_f1 + improvement)
    )
