"""Modelos de entrada e saída (Pydantic) das rotas HTTP do MJ.

Todo payload aceito ou devolvido pelo backend tem schema explícito aqui; os
serviços trabalham com os dicts canônicos da persistência e do Rule Engine.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.config import PADRAO_ID


class MensagemMJ(BaseModel):
    sessao_id: str = Field(min_length=1, max_length=64, pattern=PADRAO_ID)
    mensagem: str = Field(min_length=1, max_length=20000)


class Rolagem(BaseModel):
    """Rolagem gerada pelo Rule Engine, pronta para a interface animar o dado."""

    tipo: str
    dado: str = "d20"
    lados: int = 20
    valor: int | None = None
    rolagens: list[int] = Field(default_factory=list)
    modificador: int = 0
    total: int | None = None
    expressao: str | None = None
    dificuldade: int | None = None
    dificuldade_tipo: str | None = None
    resultado: str = "rolado"
    sucesso: bool | None = None
    critico: bool = False
    natural_1: bool = False
    vantagem: bool = False
    desvantagem: bool = False
    motivo: str | None = None
    rotulo: str | None = None
    personagem: str | None = None
    alvo: str | None = None
    seed: str | None = None
    dano: dict | None = None
    origem: str = "rule_engine"


class RespostaMJ(BaseModel):
    sessao_id: str
    resposta: str
    rolagens: list[Rolagem] = Field(default_factory=list)
    narrativa_fora_do_motor: bool = True


class NovaCampanha(BaseModel):
    titulo: str | None = Field(default=None, max_length=120)


class AtualizarCampanha(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)


class MensagemCampanha(BaseModel):
    mensagem: str = Field(min_length=1, max_length=20000)
    # Opcional para preservar compatibilidade com clientes antigos.
    operacao_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=PADRAO_ID)


class Campanha(BaseModel):
    id: str
    titulo: str
    criada_em: str
    atualizada_em: str
    ultima_mensagem: str | None = None
    total_mensagens: int = 0


class Mensagem(BaseModel):
    id: int
    papel: str
    conteudo: str
    criada_em: str
    rolagens: list[Rolagem] = Field(default_factory=list)


class CampanhaDetalhe(Campanha):
    mensagens: list[Mensagem]


class RespostaCampanha(BaseModel):
    campanha: Campanha
    resposta: str
    rolagens: list[Rolagem] = Field(default_factory=list)
    narrativa_fora_do_motor: bool = True


class AtualizarMagiasPersonagem(BaseModel):
    truques: list[str] = Field(default_factory=list, max_length=20)
    magias_preparadas: list[str] = Field(default_factory=list, max_length=50)
    espacos_totais: dict[str, int] = Field(default_factory=dict)


class NovoPersonagem(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    especie: str
    classe: str
    nivel: int = Field(default=1, ge=1, le=20)
    subclasse: str | None = None
    metodo_atributos: str = Field(default="matriz_padrao", pattern="^(matriz_padrao|compra_pontos)$")
    atributos: dict[str, int]
    antecedente: str
    aumentos_antecedente: dict[str, int]
    talento_antecedente: str | None = None
    pericias_classe: list[str] | None = Field(default=None, max_length=10)
    ferramenta_artesao: str | None = Field(default=None, max_length=80)
    heranca_draconica: str | None = Field(default=None, max_length=40)
    ferramenta_antecedente: str | None = Field(default=None, max_length=80)
    equipamento_antecedente: str | None = Field(default=None, pattern="^[AaBb]$")
    magias_iniciais: AtualizarMagiasPersonagem | None = None


class AtualizarPersonagem(BaseModel):
    ajuste_pv: int = Field(ge=-100, le=100)


class AtualizarProficienciasPersonagem(BaseModel):
    pericias_classe: list[str] = Field(min_length=1, max_length=10)
    ferramenta_artesao: str | None = Field(default=None, max_length=80)
    heranca_draconica: str | None = Field(default=None, max_length=40)
    ferramenta_antecedente: str | None = Field(default=None, max_length=80)
    equipamento_antecedente: str | None = Field(default=None, pattern="^[AaBb]$")


class AtualizarEquipamentoPersonagem(BaseModel):
    arma: str | None = Field(default=None, max_length=80)
    armadura: str | None = Field(default=None, max_length=80)
    escudo: bool = False


class SalvaguardaCondicaoFimTurno(BaseModel):
    cd: int = Field(ge=1, le=50)
    atributo: str = Field(pattern="^(forca|destreza|constituicao|inteligencia|sabedoria|carisma)$")


class AtualizarCondicaoPersonagem(BaseModel):
    operacao: str = Field(pattern="^(apply|remove|tick|query)$")
    condicao: str | None = Field(default=None, max_length=40)
    duracao: int | str | None = None
    unidades: int = Field(default=1, ge=1, le=100)
    salvaguarda_fim_turno: SalvaguardaCondicaoFimTurno | None = None


class SalvaguardaFimTurno(BaseModel):
    condicao: str = Field(min_length=1, max_length=40)
    modificador: int = Field(ge=-30, le=30)
    cd: int = Field(ge=1, le=50)


class AcaoAvancarTurno(BaseModel):
    token_id: str | None = Field(default=None, max_length=80)
    salvaguardas: list[SalvaguardaFimTurno] = Field(default_factory=list, max_length=15)
