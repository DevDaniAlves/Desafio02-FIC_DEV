from unittest.mock import Mock, patch
import requests
from src.cep_client import complement_cep, lookup_cep

CFG = {"api": {"cep_base_url": "https://viacep.com.br/ws", "timeout_segundos": 8}}


def _json_response(payload: dict, status: int = 200) -> Mock:
    response = Mock()
    response.status_code = status
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    else:
        response.raise_for_status.return_value = None
    return response


@patch("src.cep_client.requests.get")
def test_lookup_cep_complementa_municipio_e_uf(mock_get):
    mock_get.return_value = _json_response(
        {"localidade": "Caceres", "uf": "MT", "logradouro": "Rua A"}
    )
    result = lookup_cep("78200-000", CFG["api"]["cep_base_url"], timeout=8)
    assert result == {"municipio": "Caceres", "uf": "MT", "logradouro": "Rua A"}
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0].endswith("/78200000/json/")
    assert kwargs["timeout"] == 8


@patch("src.cep_client.requests.get")
def test_lookup_cep_inexistente_retorna_none(mock_get):
    mock_get.return_value = _json_response({"erro": True})
    assert lookup_cep("00000000", "https://viacep.com.br/ws") is None


@patch("src.cep_client.requests.get")
def test_lookup_cep_http_error_nao_interrompe(mock_get):
    mock_get.return_value = _json_response({}, status=503)
    assert lookup_cep("78200000", "https://viacep.com.br/ws") is None


@patch("src.cep_client.requests.get")
def test_lookup_cep_timeout_nao_interrompe(mock_get):
    mock_get.side_effect = requests.Timeout()
    assert lookup_cep("78200000", "https://viacep.com.br/ws") is None


@patch("src.cep_client.requests.get")
def test_lookup_cep_json_invalido_nao_interrompe(mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("invalid json")
    mock_get.return_value = response
    assert lookup_cep("78200000", "https://viacep.com.br/ws") is None


@patch("src.cep_client.requests.get")
def test_lookup_cep_formato_invalido_nao_chama_api(mock_get):
    assert lookup_cep("123", "https://viacep.com.br/ws") is None
    mock_get.assert_not_called()


@patch("src.cep_client.lookup_cep")
def test_complement_cep_usa_config_e_nao_lanca(mock_lookup):
    mock_lookup.return_value = {"municipio": "Cuiaba", "uf": "MT", "logradouro": "X"}
    assert complement_cep("78000-000", CFG) == {"municipio": "Cuiaba", "uf": "MT"}
    mock_lookup.return_value = None
    assert complement_cep("78000-000", CFG) == {"municipio": None, "uf": None}


def test_complement_cep_sem_url_nao_consulta():
    assert complement_cep("78200-000", {}) == {"municipio": None, "uf": None}
