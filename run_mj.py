"""Inicia uma conversa local com o DeepSeek como MJ."""

from integrations.deepseek_mj import DeepSeekMJ


def main() -> None:
    try:
        mj = DeepSeekMJ()
    except RuntimeError as exc:
        print(f"Configuração incompleta: {exc}")
        print("Cole sua chave em .env na variável TOKENHARBOR_API_KEY e execute novamente.")
        return

    print("DeepSeek MJ ativo. Digite 'sair' para encerrar.")
    historico = []
    while True:
        texto = input("\nVocê> ").strip()
        if texto.casefold() in {"sair", "exit", "quit"}:
            break
        if not texto:
            continue
        resposta = mj.responder(texto, historico)
        print(f"\nMJ> {resposta}")
        historico.extend(
            [
                {"role": "user", "content": texto},
                {"role": "assistant", "content": resposta},
            ]
        )


if __name__ == "__main__":
    main()
