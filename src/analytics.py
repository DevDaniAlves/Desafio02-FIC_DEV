"""Indicadores, exportações e gráficos."""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def build_indicators(df: pd.DataFrame) -> dict:
    times=pd.to_numeric(df.get("tempo_minutos"),errors="coerce").dropna().to_numpy(dtype=float)
    return {
      "total_registros":int(len(df)),
      "por_classificacao":df.get("classificacao",pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
      "por_categoria":df.get("categoria",pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
      "por_status":df.get("status",pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
      "tempo_medio":float(np.mean(times)) if times.size else None,
      "tempo_mediano":float(np.median(times)) if times.size else None,
      "tempo_desvio_padrao":float(np.std(times)) if times.size else None,
      "percentual_ocr":float((df.get("metodo",pd.Series(dtype=str))=="ocr").mean()*100) if len(df) else 0.0,
    }

def export_results(df: pd.DataFrame, output_dir: str | Path, csv_name: str, json_name: str) -> dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    indicators=build_indicators(df)
    df.to_csv(out/csv_name,index=False,encoding="utf-8")
    (out/json_name).write_text(json.dumps(indicators,ensure_ascii=False,indent=2,default=float),encoding="utf-8")
    return indicators

def generate_charts(df: pd.DataFrame, directory: str | Path) -> None:
    path=Path(directory); path.mkdir(parents=True,exist_ok=True)
    plots=[("categoria","Atendimentos por categoria","atendimentos_categoria.png"),("status","Atendimentos por status","atendimentos_status.png")]
    for column,title,name in plots:
        ax=df[column].fillna("Sem informação").value_counts().sort_values().plot.barh(color="#1F4E78",figsize=(9,5))
        ax.set_title(title); ax.set_xlabel("Quantidade"); ax.set_ylabel(""); plt.tight_layout(); plt.savefig(path/name,dpi=160); plt.close()
    temp=df.assign(tempo=pd.to_numeric(df["tempo_minutos"],errors="coerce")).groupby("categoria")["tempo"].mean().dropna().sort_values()
    ax=temp.plot.barh(color="#D6A84B",figsize=(9,5)); ax.set_title("Tempo médio por categoria"); ax.set_xlabel("Minutos"); ax.set_ylabel(""); plt.tight_layout(); plt.savefig(path/"tempo_medio_categoria.png",dpi=160); plt.close()
