# Baguapp (baguapp) — L2 brief

**FROZEN**

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\APPS\Baguapp`
- Status: frozen
- Phase: Prototype frozen 2026-09-08 (owner decision, CLAUDE.md §16)
- Notes: Only numbered patches for use-blocking defects with owner approval. Successor: baguapp_prod. Live at baguapp.vercel.app.

## Brain
- Current state: status=paused, phase=Prototype frozen 2026-09-08 (owner decision, CLAUDE.md §16)
  Prototype frozen by owner decision. Only numbered patches for use-blocking defects with owner approval. Successor: baguapp_prod. Live at baguapp.vercel.app.
- Last decisions:
  - CorreÃ§Ã£o: URL do filme do mascote e drift de av_mux.draw_text() entre D:\Dev e C:\APPS (2026-09-09)
  - Mascote Pixiu em 6 tomadas de 4,96s, ordem 1-2-3-4-6-5, URL queimada por ffmpeg (2026-09-09)

## CLAUDE.md rules
# BaguApp · O seu Feng Shui de Bolso
Leia este arquivo inteiro antes de mexer em qualquer coisa. Cada regra aqui
custou um erro real para ser descoberta.

## 1. O que é
- Marca: **BaguApp · O seu Feng Shui de Bolso** (não "Feng Shui no Bolso")
- Produção: **https://baguapp.vercel.app**
- Projeto Vercel: `baguapp`, time **QI** (`qi-2409`), conta `rennesan-5688`
## 2. Regra número um: uma fonte só
`vercel/index.html` é **gerado**. Nunca edite. Nunca leia como referência.

    python preparar_vercel.py     # copia o app + retratos + ícones + manifest para vercel/
traduções faltava e o coreano não existia. `Publicar na Vercel.bat` hoje roda
`preparar_vercel.py` sozinho, antes de subir, justamente para que não possa
divergir de novo.

## 3. Como publicar
Não faz perguntas. A pasta já está vinculada pelo `vercel/.vercel/project.json`.
Grava tudo em `_vercel.log`. Se a CLI disser "Logged out", rode
`Entrar na Vercel.bat` primeiro e **espere a janela confirmar** antes de fechar.
## 4. A chave da API
- **Nunca** aparece no HTML, no localStorage do celular, nem em conversa.
[line redacted by qi_handoff secret-pattern filter]
[line redacted by qi_handoff secret-pattern filter]
- Localmente as chaves ficam em `secrets/baguapp.env` (padrão QI, nunca
  commitado; só o `.env.template` entra). Para gravar uma sem que apareça na
  tela: `Guardar chave OpenRouter.bat` → `guardar_chave.py` (getpass; no
  ele mantém o campo visível e explica — não esconde o campo num servidor que
  não consegue chamar o Gemini.
- **O formato da chave não tem prefixo fixo.** Já foi `AIza…`, hoje também
  existe `AQ.…`. `extrairChave()` no app e `chave_gemini.py` nos scripts pegam
  o token mais longo com cara de chave e **validam contra a API**, nunca contra
  um prefixo. Não reintroduza validação por formato.

Localmente, `servidor_local.py` faz o mesmo papel em HTTPS (porta 8443, CA
## 5. Contrato da API Gemini
Isto não é opinião. Eu "corrigi" para camelCase baseado numa leitura apressada
da documentação e a API respondeu:

própria API sugere e refazendo a chamada. **Documentação lida por cima não
ganha de uma chamada real.** Na dúvida, chame.

### O roteador (2026-09-07)
### Quem vê o quê (regra do dono, 2026-09-08)
- A tela principal **não menciona chave**: o bloco (campo, `.txt`, "lembrar",
  avisos de servidor) existe no DOM, escondido em `#chaveBloco`, porque o
  código lê dali. Sem servidor e sem chave, o botão diz "serviço indisponível".
  selos **não nomeiam modelo**; o painel mostra.
- **`BAGU_TOKEN` é credencial de equipe, não trava de uso.** Não bloqueia a
  análise. Libera: abrir o painel (`/api/health` devolve `admin:true` e a
  escada só com ele), forçar um degrau (`x-bagu-motor`). **Sem `BAGU_TOKEN` no
  servidor o painel não abre para ninguém** — seguro por padrão; em produção
  ele precisa estar nas variáveis da Vercel.
- Entrada do painel: `Ctrl+Shift+A` ou `#admin` → "Área restrita" → credencial
  proxy) abre direto: ali não há usuário nem chave no HTML.
- A chave própria (uso sem servidor) e "sair do painel" ficam dentro do painel.

**Fase paga é configuração, não código:** pôr um modelo forte em
`BAGU_MODELO_OPENROUTER` (Claude, Gemini Pro, GLM, Qwen — a OpenRouter fala
todos pela mesma API) ou em `BAGU_EXTRA_*`.
### Determinismo — as duas camadas (do `answer_cache.py` do MapSnap)
   **não** a elimina em API hospedada.
2. **Catálogo de laudos verificados** no `localStorage` (`bagu.catalogo`, 12
   entradas, LRU): chave = sha256(planta reduzida + norte + observações +
   SCHEMA, mude `VERSAO_PROMPT`** — senão o catálogo serve laudo velho.
   Motor forçado na aba oculta pula a leitura do catálogo, mas grava.

### Referências (texto próprio, nunca cópia)
  **não citar, não traduzir, não reproduzir**.
- Ambos são servidos ao lado do app (`preparar_vercel.py` copia) e carregados
  no início; se faltarem, o prompt segue sem eles.
## 6. Idiomas — seis, sempre
**Toda string nova nasce nos seis.** Uma chave faltando não quebra visivelmente:
vira `undefined` no meio da tela, ou aborta o `applyLang()` e deixa metade da
interface no idioma anterior.
// listar as chaves que não têm os seis idiomas
```

Há um script pronto em `_testes/audit.mjs` se existir; senão reescreva — leva
dois minutos e já pegou um buraco real (`HTTP_HINT` só tinha quatro idiomas).

null-safe de propósito: um nó ausente nunca pode abortar a troca de idioma.

---
## 7. Níveis e peles
não é só tamanho — é **caráter**. Se dois níveis voltarem a se distinguir só
por um detalhe, o de cima perdeu a razão de existir:

direção — **nunca elemento**. Ver a seção 9: Wilhelm rejeita os cinco
elementos, e o `elemento` do app vem da tradição do Feng Shui. Pôr elemento
numa tabela de trigramas seria dar ao clássico uma autoridade que ele nega.
que a ponte I Ching↔Feng Shui é tradição posterior, não está no clássico.

---
## 8. O Luo Pan — regras que não se negociam
1. **A agulha aponta o norte. Sempre.** É a única parte do instrumento que não
   pode mentir. Informação da consulta vai nos anéis e na rotação do prato,
   nunca na agulha. (Um Luo Pan de verdade é usado girando o prato em relação
   à agulha — é o gesto do ofício.)
2. **Nasce parada**, apontando o norte. Só gira enquanto a análise roda.
Três regras que essa grade tem de manter:

1. **O quadro do meio é a área Centro**, que tem nota própria. A nota geral fica
## 9. I Ching
Regra do mapeamento, documentada e justificada em
`DOUTRINA - I Ching e o Bagua.md`:

Três confirmações que não foram planejadas e apareceram sozinhas:
é uma **bijeção** sobre os 64; a diagonal dá exatamente os 8 hexagramas
duplicados que encabeçam as Oito Casas; e fachada SE + setor S dá o hexagrama
Não copiar.

---
## 10. Imagens dos mestres
Geradas de graça no **ComfyUI local**, nunca por API paga (a geração de imagem
do Gemini tem `limit: 0` — cota zero, não cota esgotada).

- Host: `127.0.0.1:8740` · saída em `D:\AI\Outputs\ComfyUI\baguapp`
## 11. Orçamento
Isso não é preferência, é restrição. Se a única solução custa dinheiro, diga
isso em vez de gastar.

## 12. Convenção dos remendos
original a qualquer momento e o resultado é sempre o mesmo arquivo.

Depois de aplicar, **confira o sha256** contra a versão testada.
## 13. Como testar
O que sempre vale a pena verificar:

...(truncated — cap 150 lines)