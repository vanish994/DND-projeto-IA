from backend.persistencia import RepositorioCampanhas


def ficha_teste():
    return {
        "nome": "Vanish",
        "especie": "humano",
        "classe": "artifice",
        "nivel": 1,
        "pv_maximo": 9,
        "atributos": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 15,
            "sabedoria": 12,
            "carisma": 10,
        },
    }


def test_ficha_salva_pode_ser_vinculada_a_mais_de_uma_campanha():
    repo = RepositorioCampanhas("sqlite:///:memory:")
    jogador = "jogador-teste"
    campanha_a = repo.criar(jogador, "Campanha A")
    campanha_b = repo.criar(jogador, "Campanha B")
    ficha = ficha_teste()
    entrada = {"nome": "Vanish", "especie": "humano", "classe": "artifice"}

    salva = repo.criar_ficha_salva(jogador, entrada, ficha)
    vinculada_a = repo.vincular_ficha_salva(jogador, campanha_a["id"], salva["id"])
    vinculada_b = repo.vincular_ficha_salva(jogador, campanha_b["id"], salva["id"])

    assert salva["nome"] == "Vanish"
    assert vinculada_a is not None and vinculada_b is not None
    assert vinculada_a["id"] != vinculada_b["id"]
    assert vinculada_a["pv_atual"] == ficha["pv_maximo"]
    assert vinculada_a["campanha_id"] == campanha_a["id"]
    assert vinculada_b["campanha_id"] == campanha_b["id"]
    assert len(repo.listar_personagens(jogador, campanha_a["id"])) == 1
    assert len(repo.listar_personagens(jogador, campanha_b["id"])) == 1


def test_biblioteca_isola_fichas_por_jogador():
    repo = RepositorioCampanhas("sqlite:///:memory:")
    dono = "jogador-dono"
    outro = "jogador-outro"
    campanha_outro = repo.criar(outro, "Campanha de outra pessoa")
    salva = repo.criar_ficha_salva(
        dono,
        {"nome": "Vanish"},
        ficha_teste(),
    )

    assert repo.listar_fichas_salvas(outro) == []
    assert repo.obter_ficha_salva(outro, salva["id"]) is None
    assert repo.vincular_ficha_salva(outro, campanha_outro["id"], salva["id"]) is None
    assert repo.apagar_ficha_salva(outro, salva["id"]) is False


from backend.erros import ErroDeValidacao
from backend.schemas import NovoPersonagem
from backend.services.personagem_service import exigir_escolhas_de_criacao


def dados_criacao(**alteracoes):
    dados = {
        "nome": "Vanish",
        "especie": "humano",
        "classe": "artifice",
        "nivel": 1,
        "metodo_atributos": "matriz_padrao",
        "atributos": {
            "forca": 15,
            "destreza": 14,
            "constituicao": 13,
            "inteligencia": 12,
            "sabedoria": 10,
            "carisma": 8,
        },
        "antecedente": "acolito",
        "aumentos_antecedente": {"inteligencia": 2, "sabedoria": 1},
        "pericias_classe": ["arcanismo", "historia"],
        "ferramenta_artesao": "Ferramentas de Carpinteiro",
        "equipamento_antecedente": "A",
    }
    dados.update(alteracoes)
    return NovoPersonagem.model_validate(dados)


def test_criacao_rejeita_ficha_sem_pericias_de_classe():
    dados = dados_criacao(pericias_classe=None)
    try:
        exigir_escolhas_de_criacao(dados)
    except ErroDeValidacao as erro:
        assert "exige escolher exatamente 2 perícias" in str(erro)
    else:
        raise AssertionError("Ficha sem perícias de classe deveria ser recusada")


def test_criacao_rejeita_pericias_de_classe_repetidas():
    dados = dados_criacao(pericias_classe=["arcanismo", "arcanismo"])
    try:
        exigir_escolhas_de_criacao(dados)
    except ErroDeValidacao as erro:
        assert "Não repita perícias" in str(erro)
    else:
        raise AssertionError("Perícias repetidas deveriam ser recusadas")


def test_criacao_rejeita_artifice_sem_ferramenta_de_artesao():
    dados = dados_criacao(ferramenta_artesao=None)
    try:
        exigir_escolhas_de_criacao(dados)
    except ErroDeValidacao as erro:
        assert "ferramenta de artesão" in str(erro).lower()
    else:
        raise AssertionError("Artífice sem ferramenta deveria ser recusado")


def test_criacao_aceita_escolhas_obrigatorias_completas():
    exigir_escolhas_de_criacao(dados_criacao())
