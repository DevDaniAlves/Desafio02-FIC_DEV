"""Indicadores, exportações e gráficos

O CSV preserva todos os registros já tratados (inclusive incompletos, inválidos
e duplicados). Totais de classificação e método usam a base completa. Recortes
por categoria, status, município e estatísticas de tempo usam só registros
válidos, para não misturar falha de extração com o resultado operacional.
Artefatos são gerados mesmo sem linhas: CSV com cabeçalho, JSON zerado e cinco
PNGs legíveis (categoria, tempo médio por categoria, status, município e método).
Problemas de classificação entram no log de processamento.
"""

from __future__ import annotations

from pathlib import Path
import json
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CSV_COLUMNS = [
    "protocolo",
    "data",
    "solicitante",
    "email",
    "categoria",
    "status",
    "cep",
    "municipio",
    "uf",
    "tempo_minutos",
    "descricao",
    "solucao",
    "observacoes",
    "classificacao",
    "motivos",
    "documento",
    "pagina",
    "metodo",
]
CHART_SPECS = (
    ("categoria", "Atendimentos por categoria", "atendimentos_categoria.png"),
    ("status", "Atendimentos por status", "atendimentos_status.png"),
    ("municipio", "Atendimentos por município", "atendimentos_municipio.png"),
    ("metodo", "Atendimentos por método de extração", "atendimentos_metodo.png"),
)
CLASSIFICACOES = ("valido", "incompleto", "invalido", "duplicado")
OCR_METHODS = {"ocr", "misto", "ocr_pendente"}
MISSING_LABEL = "Sem informação"


def _column(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series(dtype=object, index=df.index)


def _label_missing(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    return text.mask(text.eq("") | text.str.lower().isin({"nan", "none"}), MISSING_LABEL)


def valid_records(df: pd.DataFrame) -> pd.DataFrame:
    """Filtro Pandas dos registros classificados como válidos."""
    if df.empty or "classificacao" not in df.columns:
        return df.copy()
    return df.loc[_column(df, "classificacao").fillna("").eq("valido")].copy()


def _classification_counts(df: pd.DataFrame) -> dict[str, int]:
    series = _column(df, "classificacao").fillna("").astype(str).str.strip()
    return {name: int(series.eq(name).sum()) for name in CLASSIFICACOES}


def _document_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    labeled = _label_missing(_column(df, "documento"))
    return int(labeled[labeled != MISSING_LABEL].nunique())


def _grouped_counts(series: pd.Series) -> dict[str, int]:
    """Agrupamento e agregação de quantidade por dimensão."""
    if series.empty:
        return {}
    work = pd.DataFrame({"dimensao": _label_missing(series)})
    grouped = work.groupby("dimensao", dropna=False).size().sort_values(ascending=False)
    return {str(key): int(value) for key, value in grouped.items()}


def tempo_stats(values: np.ndarray) -> dict[str, float | None]:
    """Média, mediana e desvio-padrão amostral com NumPy."""
    times = np.asarray(values, dtype=float)
    times = times[np.isfinite(times)]
    if times.size == 0:
        return {
            "tempo_medio": None,
            "tempo_mediano": None,
            "tempo_desvio_padrao": None,
        }
    return {
        "tempo_medio": float(np.mean(times)),
        "tempo_mediano": float(np.median(times)),
        "tempo_desvio_padrao": float(np.std(times, ddof=1)) if times.size > 1 else 0.0,
    }


def _mean_time_by_category(df: pd.DataFrame) -> dict[str, float]:
    if df.empty or "tempo_minutos" not in df.columns:
        return {}
    work = pd.DataFrame(
        {
            "categoria": _label_missing(_column(df, "categoria")),
            "tempo": pd.to_numeric(df["tempo_minutos"], errors="coerce"),
        }
    )
    means = (
        work.groupby("categoria", dropna=False)["tempo"]
        .agg(lambda series: float(np.mean(series.dropna().to_numpy(dtype=float))) if series.dropna().size else np.nan)
        .dropna()
        .sort_values()
    )
    return {str(key): float(value) for key, value in means.items()}


def _ocr_share(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    method = _column(df, "metodo").fillna("").astype(str).str.strip().str.lower()
    return float(method.isin(OCR_METHODS).mean() * 100)


def _count_series(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    work = pd.DataFrame({"dimensao": _label_missing(_column(df, column))})
    return work.groupby("dimensao", dropna=False).size().sort_values()


def _tempo_medio_series(df: pd.DataFrame) -> pd.Series:
    if df.empty or "tempo_minutos" not in df.columns:
        return pd.Series(dtype=float)
    work = pd.DataFrame(
        {
            "categoria": _label_missing(_column(df, "categoria")),
            "tempo": pd.to_numeric(df["tempo_minutos"], errors="coerce"),
        }
    )
    return (
        work.groupby("categoria", dropna=False)["tempo"]
        .mean()
        .dropna()
        .sort_values()
    )


def build_indicators(df: pd.DataFrame) -> dict:
    """Totais da base completa; categoria, status, município e tempo só nos válidos."""
    valid = valid_records(df)
    times = (
        pd.to_numeric(_column(valid, "tempo_minutos"), errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )
    stats = tempo_stats(times)
    por_classificacao = _classification_counts(df)
    return {
        "total_documentos": _document_count(df),
        "total_registros": int(len(df)),
        "registros_validos": por_classificacao["valido"],
        "registros_incompletos": por_classificacao["incompleto"],
        "registros_invalidos": por_classificacao["invalido"],
        "registros_duplicados": por_classificacao["duplicado"],
        "por_classificacao": por_classificacao,
        "por_categoria": _grouped_counts(_column(valid, "categoria")),
        "por_status": _grouped_counts(_column(valid, "status")),
        "por_municipio": _grouped_counts(_column(valid, "municipio")),
        "por_metodo": _grouped_counts(_column(df, "metodo")),
        "tempo_medio": stats["tempo_medio"],
        "tempo_mediano": stats["tempo_mediano"],
        "tempo_desvio_padrao": stats["tempo_desvio_padrao"],
        "tempo_medio_por_categoria": _mean_time_by_category(valid),
        "percentual_ocr": _ocr_share(df),
    }


def log_processing_problems(df: pd.DataFrame) -> int:
    """Grava no log cada registro que não ficou válido (incompleto, inválido ou duplicado)."""
    if df.empty or "classificacao" not in df.columns:
        return 0
    problems = df.loc[_column(df, "classificacao").fillna("") != "valido"]
    for item in problems.to_dict("records"):
        logging.warning(
            "Problema no registro: protocolo=%s classificacao=%s motivos=%s documento=%s pagina=%s",
            item.get("protocolo", ""),
            item.get("classificacao", ""),
            item.get("motivos", ""),
            item.get("documento", ""),
            item.get("pagina", ""),
        )
    return int(len(problems))


def _csv_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CSV_COLUMNS)
    ordered = [column for column in CSV_COLUMNS if column in df.columns]
    extra = [column for column in df.columns if column not in CSV_COLUMNS]
    return df.loc[:, ordered + extra]


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f"Tipo não serializável: {type(value)!r}")


def export_results(
    df: pd.DataFrame, output_dir: str | Path, csv_name: str, json_name: str
) -> dict:
    """Escreve CSV (utf-8-sig), JSON de indicadores e registra problemas no log."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    indicators = build_indicators(df)
    _csv_frame(df).to_csv(out / csv_name, index=False, encoding="utf-8-sig")
    (out / json_name).write_text(
        json.dumps(indicators, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    problems = log_processing_problems(df)
    logging.info(
        "Exportação: %s documento(s), %s registro(s), %s válido(s), %s com problema(s)",
        indicators["total_documentos"],
        indicators["total_registros"],
        indicators["registros_validos"],
        problems,
    )
    return indicators


def _save_barh(
    series: pd.Series, title: str, xlabel: str, destination: Path, color: str, as_int: bool
) -> None:
    count = max(len(series), 1)
    fig, ax = plt.subplots(figsize=(9, max(3.8, 0.45 * count + 1.4)))
    if series.empty:
        ax.text(
            0.5,
            0.5,
            "Sem dados para exibir",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        labels = [str(label) for label in series.index]
        values = series.to_numpy(dtype=float)
        bars = ax.barh(labels, values, color=color)
        formatted = [f"{int(round(value))}" if as_int else f"{value:.1f}" for value in values]
        ax.bar_label(bars, labels=formatted, padding=4, fontsize=9)
        ax.set_xlabel(xlabel)
        ax.set_xlim(0, max(values) * 1.18 if max(values) else 1)
        ax.grid(axis="x", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(destination, dpi=160)
    plt.close(fig)


def generate_charts(df: pd.DataFrame, directory: str | Path) -> list[Path]:
    """Gera os cinco PNGs; série vazia vira figura com 'Sem dados para exibir'."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    valid = valid_records(df)
    written: list[Path] = []
    for column, title, name in CHART_SPECS:
        source = df if column == "metodo" else valid
        destination = path / name
        _save_barh(
            _count_series(source, column), title, "Quantidade", destination, "#1F4E78", True
        )
        written.append(destination)
    tempo_path = path / "tempo_medio_categoria.png"
    _save_barh(
        _tempo_medio_series(valid),
        "Tempo médio por categoria",
        "Minutos",
        tempo_path,
        "#D6A84B",
        False,
    )
    written.append(tempo_path)
    return written
