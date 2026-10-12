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
