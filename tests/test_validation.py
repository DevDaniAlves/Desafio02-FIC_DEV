from src.validation import validate_record, normalize_category

CATS={"categorias_oficiais":[{"nome":"Python e bibliotecas","variacoes":["python","pip"]}]}

def test_valid_record():
    record={"protocolo":"AT-001","data":"01/08/2026","email":"a@b.com","cep":"78200-000","categoria":"pip","tempo_minutos":"20","solicitante":"Ana","descricao":"Erro"}
    classification,reasons,normalized=validate_record(record,CATS)
    assert classification=="valido" and not reasons
    assert normalized["categoria_normalizada"]=="Python e bibliotecas"

def test_invalid_email():
    record={"protocolo":"AT-001","data":"01/08/2026","email":"invalido","cep":"78200-000","categoria":"python","tempo_minutos":"20","solicitante":"Ana","descricao":"Erro"}
    assert "email_invalido" in validate_record(record,CATS)[1]
