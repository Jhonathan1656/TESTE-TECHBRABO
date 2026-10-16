# Design system da Central de Dados

Guia visual e de interação do protótipo. Vale para todo o frontend (`frontend/src`): componentes só usam os tokens de `styles/tokens.css`, nunca valores soltos.

## 1. Princípios

A Central de Dados é uma ferramenta interna e densa: o analista passa o dia comparando tabelas de preço. Por isso:

1. **O dado vem antes da interface.** Superfícies planas separadas por bordas de 1 px, sem sombras decorativas (sombra só em camadas sobrepostas: diálogo, toast e menu móvel). A barra lateral é clara para não competir com o conteúdo.
2. **Uma ação principal por tela.** O botão primário (verde-petróleo sólido) aparece uma vez por contexto: "Aprovar e publicar", "Cotar", "Enviar e processar". O resto é secundário, contornado ou discreto.
3. **Cor nunca sozinha.** Todo estado tem texto ou ícone além da cor. Isso vale para os selos de situação, as células com erro (cor de fundo, barra lateral e o nome acessível com a severidade) e os indicadores do painel (o número fica em preto e o ícone colorido reforça o texto de apoio).
4. **Densidade com respiro.** Corpo em 14 px, grade de 4 px e números tabulares, para que as colunas de preço alinhem pelo dígito.

## 2. Tokens

### Cor

Paleta neutra fria, com um leve tom verde que conversa com a marca, e um verde-petróleo como cor primária: remete à saúde sem cair no ciano hospitalar nem no azul genérico de SaaS.

| Papel | Token | Valor | Contraste |
|---|---|---|---|
| Texto | `--color-text` | `#141a1f` | 17,5:1 no branco |
| Texto secundário | `--color-text-muted` | `#49525b` | 7,9:1 no branco |
| Texto de apoio | `--color-text-subtle` | `#5f6870` | 5,7:1 no branco; 5,2:1 no fundo |
| Borda de campo | `--color-border-input` | `#7d8790` | 3,7:1 (limite de componente) |
| Primária | `--color-primary` | `#0b6b63` | 6,4:1 com texto branco |
| Erro | `--color-error` | `#b42318` | 6,1:1 no fundo de erro |
| Alerta | `--color-warning` | `#8f4400` | 6,5:1 no fundo de alerta |
| Sucesso | `--color-success` | `#0d6e3c` | 5,8:1 no fundo de sucesso |
| Informação | `--color-info` | `#1d5bb8` | 5,9:1 no fundo informativo |

Todos os pares de texto passam no nível AA da WCAG 2.2 (4,5:1) e os limites de componente e o anel de foco passam em 3:1. Cada status tem três tons: tinta (texto e ícone), fundo suave e borda.

A versão anterior usava `#8693a3` para datas e textos de apoio (3,2:1, abaixo do mínimo); foi substituída por `--color-text-subtle`.

### Tipografia

- **IBM Plex Sans** (fonte variável) para interface e dados, com algarismos tabulares (`tabular-nums`) em tabelas, preços e indicadores.
- **IBM Plex Mono** só para códigos: hash do documento, registro ANS e o texto bruto extraído da tabela.
- As fontes são **servidas pelo próprio app** (pacotes `@fontsource`), sem chamada ao Google Fonts. Isso evita uma dependência externa e o envio do IP do usuário a terceiros.

| Token | Tamanho | Uso |
|---|---|---|
| `--text-2xs` | 11 px | rótulos em caixa alta, sempre com espaçamento de 0,06em |
| `--text-xs` | 12 px | selos, valores anteriores na grade |
| `--text-sm` | 13 px | textos de apoio, botões pequenos |
| `--text-base` | 14 px | corpo |
| `--text-md` | 16 px | títulos de card; campos de formulário no celular, para evitar zoom no iOS |
| `--text-xl` | 24 px | título da página |
| `--text-2xl` | 30 px | número dos indicadores |

Regras tipográficas aplicadas aos textos (em `messages.pt-BR.ts` e nas mensagens do backend): aspas curvas (“ ”), reticências como um caractere (…), meia-risca em intervalos (44–48) e títulos com `text-wrap: balance`.

### Espaço, forma e movimento

- Espaçamento em múltiplos de 4 px (`--space-1` a `--space-12`).
- Raios de 4 a 10 px. Cards usam 10 px e controles usam 8 px.
- Controles com 36 px de altura; os pequenos têm 30 px, acima do mínimo de 24 px da WCAG 2.2.
- Transições de 120 ms a 200 ms, só de cor, opacidade e posição. Com `prefers-reduced-motion`, as durações vão a zero e o *skeleton* para de pulsar.

## 3. Componentes

| Componente | Arquivo | Notas |
|---|---|---|
| `Button` / `ButtonLink` | `shared/components/Button.tsx` | variantes `primary`, `secondary`, `danger` (contornado), `destructive` (sólido, para confirmar exclusões) e `ghost`; botão só com ícone exige `aria-label`; navegação usa `ButtonLink`, que é um link de verdade |
| `Badge` | `Badge.tsx` | tons de status; ponto e ícone opcionais, sempre com texto |
| `Card` | `Card.tsx` | `section` nomeada pelo próprio título |
| `PageHeader` | `PageHeader.tsx` | trilha de navegação, título, status e ações; define o título da aba (`<title>` do React 19) |
| `Dialog` | `Dialog.tsx` | `<dialog>` nativo: foco preso, Esc fecha, fundo inerte, botão "Fechar" e foco devolvido ao gatilho |
| `TableScroll` | `TableScroll.tsx` | rolagem horizontal das tabelas, focável e nomeada para uso pelo teclado |
| `LoadingState` / `EmptyState` / `ErrorState` | `States.tsx` | *skeleton* em vez de spinner; vazio e erro sempre com próximo passo |
| Toasts | `toast.tsx` | região `aria-live` que não rouba o foco; somem em 5 s e podem ser dispensados |

## 4. Padrões de interação

- **Estado na URL.** O filtro da fila (`/batches?status=published`) e a busca de planos (`/plans?q=…&inactive=1`) sobrevivem a recarregar a página e podem ser compartilhados.
- **Ação destrutiva pede confirmação.** "Retirar do cotador" e "Rejeitar" abrem diálogo com botão vermelho sólido. "Excluir plano do lote" não pede confirmação porque é reversível na hora com "Incluir".
- **Erros junto do campo.** Idades inválidas na cotação e valor mal formatado na correção mostram a mensagem abaixo do campo, ligada por `aria-describedby`, e o foco vai para o campo.
- **Navegação adaptável.** Barra lateral a partir de 1024 px. Abaixo disso, barra superior com menu recolhível, que fecha com Esc e devolve o foco ao botão.
- **Carregamento por rota.** Cada página é um *chunk* separado (`React.lazy`); o login e o esqueleto da aplicação carregam primeiro.

## 5. Acessibilidade: o que foi verificado

Meta: WCAG 2.2 nível AA.

- **Varredura automática.** O motor de regras [@accesslint/core](https://www.npmjs.com/package/@accesslint/core) rodou sobre o app em execução, em 16 telas e estados:
  - login, painel, fila (dois filtros), revisão do lote com o diálogo da célula aberto, importação, cotação (formulário e resultado), lista e histórico de planos, fontes com registros abertos e página 404;
  - celular de 390 px, com o menu aberto e fechado.

  Resultado final: **zero violações**. As falhas encontradas no caminho foram corrigidas:
  - diálogos fechados sem nome acessível;
  - link de tabela distinguível só pela cor;
  - tabela rolável inacessível pelo teclado;
  - salto de nível de título;
  - página 404 sem `h1`.
- **Checagem manual:**
  - link "Pular para o conteúdo" como primeira parada do Tab;
  - foco movido para o conteúdo a cada troca de rota;
  - anel de foco visível em todos os controles;
  - menu móvel fechando com Esc;
  - nenhuma rolagem horizontal da página a 390 px;
  - cada célula da grade de preços com nome acessível completo ("Plano, faixa 44–48: R$ 878,13. antes R$ 716,88 (+22,49%). Alerta").
- **Testes automatizados** (`npm test`) cobrem:
  - o nome acessível das células;
  - o diálogo (nome, descrição, fechar e estado ocupado);
  - o título da aba e a trilha de navegação;
  - o filtro da fila lido da URL.
- **Ainda depende de teste com pessoas:** leitores de tela reais (NVDA, VoiceOver) e uso só por teclado nas sessões longas de revisão.

## 6. Decisões deliberadas

- **Sem tema escuro, por enquanto.** É uma ferramenta de escritório, usada em telas densas de tabela. Os tokens são semânticos, então um tema escuro é um segundo bloco de variáveis, a ser validado com o mesmo script de contraste.
- **Sem biblioteca de componentes.** O app tem poucos componentes e eles são simples. CSS com tokens e elementos nativos (`dialog`, `details`, `input type=file` dentro de `label`) entregam acessibilidade sem dependências extras.

## 7. Referências

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) e a metodologia WCAG-EM.
- [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines) (Vercel).
- [Practical Typography](https://practicaltypography.com), de Matthew Butterick.
- [React: lazy, use e Context como provider](https://react.dev/reference/react) (React 19).
