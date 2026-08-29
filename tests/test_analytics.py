import json
import numpy as np
import pandas as pd

from src.analytics import (
    MISSING_LABEL,
    build_indicators,
    export_results,
    generate_charts,
    tempo_stats,
    valid_records,
)
from src.pipeline import metodo_from_pages, metodos_por_pagina, normalize_extraction_method


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protocolo": "AT-001",
                "documento": "a.pdf",
                "classificacao": "valido",
                "categoria": "Hardware",
                "status": "Concluido",
                "municipio": "Cáceres",
                "metodo": "extracao_direta",
                "tempo_minutos": 10,
            },
            {
                "protocolo": "AT-002",
                "documento": "a.pdf",
                "classificacao": "valido",
                "categoria": "Hardware",
                "status": "Pendente",
                "municipio": "Cáceres",
                "metodo": "ocr",
                "tempo_minutos": 20,
            },
            {
                "protocolo": "AT-003",
                "documento": "b.pdf",
                "classificacao": "incompleto",
                "categoria": "Software",
                "status": "Em atendimento",
                "municipio": "",
                "metodo": "ocr",
                "tempo_minutos": 30,
            },
            {
                "protocolo": "AT-004",
                "documento": "b.pdf",
                "classificacao": "invalido",
                "categoria": "  ",
                "status": "Concluido",
                "municipio": "Cuiabá",
                "metodo": "extracao_direta",
                "tempo_minutos": "nao-numero",
            },
            {
                "protocolo": "AT-001",
                "documento": "c.pdf",
                "classificacao": "duplicado",
                "categoria": "Hardware",
                "status": "Concluido",
                "municipio": "Cáceres",
                "metodo": "ocr",
                "tempo_minutos": 99,
            },
        ]
    )


def test_tempo_stats_com_numpy():
    stats = tempo_stats(np.array([10.0, 20.0, 30.0]))
    assert stats["tempo_medio"] == 20.0
    assert stats["tempo_mediano"] == 20.0
    assert stats["tempo_desvio_padrao"] == float(np.std([10.0, 20.0, 30.0], ddof=1))


def test_tempo_stats_vazio_e_unico():
    vazio = tempo_stats(np.array([]))
    assert vazio["tempo_medio"] is None
    unico = tempo_stats(np.array([12.0]))
    assert unico["tempo_medio"] == 12.0
    assert unico["tempo_desvio_padrao"] == 0.0


def test_valid_records_filtra_classificacao():
    valid = valid_records(_sample_df())
    assert len(valid) == 2
    assert set(valid["protocolo"]) == {"AT-001", "AT-002"}


def test_build_indicators_totais_e_dimensoes():
    indicators = build_indicators(_sample_df())
    times = np.array([10.0, 20.0])

    assert indicators["total_documentos"] == 3
    assert indicators["total_registros"] == 5
    assert indicators["registros_validos"] == 2
    assert indicators["registros_incompletos"] == 1
    assert indicators["registros_invalidos"] == 1
    assert indicators["registros_duplicados"] == 1
    assert indicators["por_classificacao"] == {
        "valido": 2,
        "incompleto": 1,
        "invalido": 1,
        "duplicado": 1,
    }
    assert indicators["tempo_medio"] == 15.0
    assert indicators["tempo_mediano"] == 15.0
    assert indicators["tempo_desvio_padrao"] == float(np.std(times, ddof=1))
    assert indicators["por_categoria"] == {"Hardware": 2}
    assert indicators["por_status"]["Concluido"] == 1
    assert indicators["por_status"]["Pendente"] == 1
    assert indicators["por_municipio"] == {"Cáceres": 2}
    assert MISSING_LABEL not in indicators["por_municipio"]
    assert indicators["por_metodo"]["ocr"] == 3
    assert indicators["por_metodo"]["extracao_direta"] == 2
    assert indicators["tempo_medio_por_categoria"]["Hardware"] == 15.0
    assert indicators["percentual_ocr"] == 60.0


def test_build_indicators_dataframe_vazio():
    indicators = build_indicators(pd.DataFrame())
    assert indicators["total_documentos"] == 0
    assert indicators["total_registros"] == 0
    assert indicators["registros_validos"] == 0
    assert indicators["registros_incompletos"] == 0
    assert indicators["registros_invalidos"] == 0
    assert indicators["registros_duplicados"] == 0
    assert indicators["por_classificacao"] == {
        "valido": 0,
        "incompleto": 0,
        "invalido": 0,
        "duplicado": 0,
    }
    assert indicators["tempo_medio"] is None
    assert indicators["por_municipio"] == {}
    assert indicators["por_metodo"] == {}
    assert indicators["percentual_ocr"] == 0.0


def test_tempo_ignora_incompletos_invalidos_e_duplicados():
    indicators = build_indicators(_sample_df())
    assert indicators["tempo_medio"] != 99
    assert indicators["tempo_medio"] != 30


def test_export_results_e_graficos(tmp_path):
    df = _sample_df()
    indicators = export_results(df, tmp_path, "atendimentos.csv", "indicadores.json")
    payload = json.loads((tmp_path / "indicadores.json").read_text(encoding="utf-8"))
    assert payload["total_documentos"] == indicators["total_documentos"] == 3
    assert payload["registros_validos"] == 2
    assert (tmp_path / "atendimentos.csv").exists()

    charts = generate_charts(df, tmp_path / "graficos")
    names = {path.name for path in charts}
    assert names == {
        "atendimentos_categoria.png",
        "atendimentos_status.png",
        "atendimentos_municipio.png",
        "atendimentos_metodo.png",
        "tempo_medio_categoria.png",
    }
    assert all(path.exists() and path.stat().st_size > 0 for path in charts)


def test_normalize_extraction_method_e_paginas():
    assert normalize_extraction_method("ocr_pendente") == "ocr"
    assert normalize_extraction_method("extracao_direta") == "extracao_direta"
    pages = [
        {"pagina": 1, "metodo": "extracao_direta"},
        {"pagina": 2, "metodo": "ocr_pendente"},
    ]
    assert metodos_por_pagina(pages) == {1: "extracao_direta", 2: "ocr"}
    assert metodo_from_pages(pages) == "misto"
    assert metodo_from_pages([{"pagina": 1, "metodo": "ocr_pendente"}]) == "ocr"
