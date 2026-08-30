from unittest.mock import patch

import requests

from src.app_streamlit import ALL_CATEGORIES, ask_api, check_health, load_categories


def test_load_official_categories():
    names = load_categories()
    assert "Python e bibliotecas" in names
    assert ALL_CATEGORIES == "(todas)"


@patch("src.app_streamlit.requests.get")
def test_health_ok(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "ok", "modo": "recuperacao_local"}
    mock_get.return_value.raise_for_status.return_value = None
    assert check_health("http://127.0.0.1:8000")["status"] == "ok"


@patch("src.app_streamlit.requests.get", side_effect=requests.ConnectionError)
def test_health_down(_mock_get):
    assert check_health("http://127.0.0.1:8000") is None


@patch("src.app_streamlit.requests.post")
def test_ask_api_sends_category(mock_post):
    mock_post.return_value.raise_for_status.return_value = None
    mock_post.return_value.json.return_value = {"resposta": "ok", "fontes": []}
    ask_api("http://127.0.0.1:8000", "erro no pip", 3, "Python e bibliotecas", None)
    _args, kwargs = mock_post.call_args
    assert kwargs["json"] == {
        "pergunta": "erro no pip",
        "top_k": 3,
        "categoria": "Python e bibliotecas",
    }
