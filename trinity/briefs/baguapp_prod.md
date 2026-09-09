# BaguApp Prod (baguapp_prod) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\BaguApp_Prod`
- Status: active
- Phase: Marco zero — spec + docs, no code yet
- Notes: The real BaguApp product; inherits from the frozen prototype at C:\APPS\Baguapp. Mould for MilkWise.

## Brain
- Current state: status=active, phase=Marco zero — spec + docs, no code yet
  Registered 2026-09-08. The real BaguApp product; inherits from the frozen prototype at C:\APPS\Baguapp. Mould for MilkWise.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# BaguApp — o aplicativo de verdade
protótipo: cada regra aqui custou um erro real para ser descoberta lá.

---
## 0. Regra zero: o protótipo está congelado
protótipo parecer errado, anote em `docs/` e siga — não corrija lá.

Consequência boa: como o protótipo não evolui, **copiar** os arquivos dele
para cá é seguro. O perigo de "duas cópias que se afastam" só existe quando
as duas mudam. Aqui só esta muda.
## 1. O que é o produto
cada símbolo é explicado e as correções vêm **integradas a cada passo**, não
numa seção separada. O Resumo do Laudo é mais formal, técnico e longo que o
da Jornada.
## 2. O que herdar do protótipo (copiar uma vez, de `C:\APPS\Baguapp`)
| `iching_temas.json` | os 64 temas + leitura para um cômodo, **texto próprio** (a edição canônica é protegida; nada dela foi reproduzido) | copiar tal qual; expandir se precisar, nunca colar fonte |
| `fengshui_referencia.json` | 25 princípios do Zangshu (chinês clássico, domínio público) com explicação e aplicação à casa, nossas | copiar tal qual |
| `iching_mapeamento.json` | Céu Posterior: direção → trigrama → área | copiar |
| `DOUTRINA - I Ching e o Bagua.md` (já em `docs/`) | a regra setor = interior, fachada = exterior, e por quê | é lei |
| `vercel/api/analisar.js` + `health.js` | roteador de motores com escada, validação de estrutura e **cânone**, castigo de modelo sem cota, credencial de equipe | base do serviço de análise; refatorar em módulos, manter o comportamento |
| `BaguApp Prototipo.html` | tabelas dos seis idiomas (`I18N`, `UI`, `AREA_T`, `ELEM_T`, `DIR_T`, `TRI_*`, `RING`, `LBL`, `P`, `HTTP_HINT`), `SCHEMA`, `SYSTEM_INSTRUCTION`, `tabelaIChing()`, `referenciaFengShui()`, o Luo Pan (`drawLuoPan`), a grade do Bagua (`gradeBagua`), os trigramas (`trigramasEmJogo`), `prepararImagem()`, o catálogo (`chaveCatalogo`, `catalogoLer/Gravar`) | **extrair** para arquivos próprios (JSON para dados, módulos JS para lógica). É o item "separar os dados do HTML" que o protótipo deixou em aberto |
Não herdar: os `_remendos/` (mecanismo do arquivo único; aqui o git é o diff),
o login de `localStorage` (é de mentira), a aba oculta como está (o painel
aqui é uma rota autenticada de verdade).
## 3. Decisões que já valem (não reabrir sem motivo novo)
1. **Chave nunca no cliente.** Só em variáveis de ambiente do servidor. Nem em
   HTML, nem em `localStorage`, nem em conversa. Localmente: `secrets/<projeto>.env`.
2. **O usuário só tem direito de rodar o programa.** Chave, motor, modelo e
   programa). A tela do usuário não menciona chave nem nomeia modelo.
3. **Roteador de motores com validação.** Escada de provedores; cada degrau é
   conferido — estrutura e **cânone** (cada leitura do I Ching cita, por hanzi
   que respondeu vai na resposta (para o painel, não para o usuário).
4. **Duas camadas de determinismo** (do `answer_cache.py` do MapSnap):
   `temperature 0` (+ `seed`), e um **catálogo de laudos verificados** — a
   usuário é texto nosso. Nunca reproduzir a tradução. A tabela de trigramas
   **não tem coluna de elemento** — Wilhelm rejeita os cinco elementos; o
   elemento é material de Feng Shui, fica no cartão da zona.
6. **A estrutura é calculada, a prosa é do modelo.** Hexagramas, setores,
7. **Seis idiomas, sempre**: pt, en, fr, es, ja, ko. Toda string nasce nos
   seis; há auditoria que sai com código 1 se faltar uma.
8. **Luo Pan**: a agulha aponta o norte, sempre; nasce parada; 子 centrado em
   0°; ordem canônica das 24 montanhas; Céu Posterior N=坎 NE=艮 L=震 SE=巽
   S=離 SO=坤 O=兌 NO=乾. Ver `ROTEIRO - Luo Pan em 4 camadas.md` no protótipo
   qualidade decide, não custo.
10. **Vercel Hobby veta uso comercial.** No dia do primeiro real: Vercel Pro ou
    Cloudflare Pages + Workers (recomendado: zero, comercial, sem o limite de
## 4. Arquitetura proposta (três fases)
(nunca montar a estrutura à mão) e validar com `qi_validator.py`.

---
## 5. Perguntas em aberto — responder no início da primeira sessão
9. Hospedagem do v2: projeto **novo** na Vercel (`baguapp-v2`, URL própria) — a URL do protótipo nunca pode quebrar.

---
## 6. Armadilhas já pagas (as que mais importam; a lista inteira está no protótipo)
- **Barra invertida não sobrevive a heredoc** no Bash daqui: `\\` vira `\`, `\b` vira backspace. Regex em script inline: `chr(92)`, ou a ferramenta de escrita.
- `getpass` no Windows lê do console e **ignora pipe** — de propósito; a chave só entra por uma pessoa num terminal.
- Uma pasta movida quebra tudo que aponta para ela (386 arquivos no OpenClaw). **Antes de mover, `grep`.** Vale para o protótipo se um dia virar `Baguapp_Demo`; esta pasta já nasceu com o nome definitivo.
## 7. Como o dono trabalha
- Respostas completas e estruturadas, com tabelas, e o **contra-argumento mais forte primeiro**. Não enfeite.
- Prefere script automático a passo manual. Se não consegue clicar em algo, direcione-o com precisão — ele clica.
- Ele corrige quando você erra, e tem razão com frequência suficiente para você verificar antes de discordar.
- Publicar é ação dele (`.bat`). Chave nunca passa pela conversa.

## Entry points
- none found
