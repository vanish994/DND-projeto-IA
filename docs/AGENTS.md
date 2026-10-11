# Regras de UI para agentes

Antes de criar ou alterar qualquer interface, leia docs/DESIGN_SYSTEM.md e use os tokens de frontend/design-tokens.css.

## Regras obrigatórias

- Na tela de conversa, use app-shell de uma viewport (100dvh com fallback 100vh) sem rolagem da página. Cabeçalho e compositor permanecem fixos; somente a lista de mensagens rola internamente. Reavalie a altura ao abrir o teclado e respeite safe-area-inset-bottom.
- Use os tokens CSS existentes. Não introduza cores hexadecimais avulsas fora de frontend/design-tokens.css sem atualizar este sistema e a documentação.
- Preserve o modo escuro carvão e o acento âmbar; use o âmbar para ações, foco e pequenos destaques, nunca como fundo de parágrafos longos.
- Alvos interativos devem ter pelo menos 48 por 48 px; não dependa de hover para revelar ações.
- Mantenha contraste WCAG AA, foco visível e texto de estado além da cor. Respeite prefers-reduced-motion e safe-area-inset-bottom no compositor fixo.
- Use HTML semântico, rótulos acessíveis e mensagens em português do Brasil. Preserve a distinção visual entre jogador e MJ.
- A tela inicial do jogador é enxuta: mostrar campanhas recentes, ação Retomar e ação Nova campanha. Não exibir texto promocional, status técnico do motor ou seções de especificação (como contraste e regras de experiência); mover explicações para Ajuda/Configurações.
- A campanha deve aparecer como contexto da conversa; trocar de campanha não deve apagar seu histórico.
- Tales RPG e AI Dungeon são referências de agência narrativa e continuidade. Não copie nomes, marcas, layout ou assets dessas plataformas.
- Este frontend é HTML/CSS/JavaScript sem framework; não acrescente Tailwind ou uma biblioteca de componentes só para reproduzir este sistema.
