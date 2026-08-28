from src.validation import validate_record, normalize_category, extract_fields, is_missing

CATS={"categorias_oficiais":[{"nome":"Python e bibliotecas","variacoes":["python","pip"]}]}

def test_valid_record():
    record={"protocolo":"AT-001","data":"01/08/2026","email":"a@b.com","cep":"78200-000","categoria":"pip","tempo_minutos":"20","solicitante":"Ana","descricao":"Erro"}
    classification,reasons,normalized=validate_record(record,CATS)
    assert classification=="valido" and not reasons
    assert normalized["categoria_normalizada"]=="Python e bibliotecas"

def test_invalid_email():
    record={"protocolo":"AT-001","data":"01/08/2026","email":"invalido","cep":"78200-000","categoria":"python","tempo_minutos":"20","solicitante":"Ana","descricao":"Erro"}
    assert "email_invalido" in validate_record(record,CATS)[1]

def test_placeholder_solicitante_incompleto():
    record={"protocolo":"AT-001","data":"01/08/2026","email":"a@b.com","cep":"78200-000","categoria":"python","tempo_minutos":"20","solicitante":"[vazio]","descricao":"Erro"}
    classification, reasons, _ = validate_record(record, CATS)
    assert classification == "incompleto"
    assert "solicitante_ausente" in reasons

def test_extract_fields_protocolo_e_email():
    text = "Protocolo AT-001 Data 01/08/2026 Solicitante Ana E-mail a@b.com Categoria pip Status Pendente CEP / cidade 78200-000 Tempo 20 min Problema Falha Solucao Ok Observacoes teste"
    fields = extract_fields(text)
    assert fields["protocolo"] == "AT-001"
    assert fields["email"] == "a@b.com"
    assert fields["status"] == "Pendente"

def test_is_missing_markers():
    assert is_missing("[vazio]")
    assert is_missing("")
    assert not is_missing("Ana")
