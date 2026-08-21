# Uptime pinger

Mantém os serviços do Render acordados e publica uma página de status no GitHub Pages.

- **GitHub Actions** roda `scripts/ping.py` a cada 10 minutos e commita `docs/data/status.json`.
- **GitHub Pages** serve `docs/index.html`, que lê esse JSON e mostra status, latência e uptime.

O GitHub Pages não executa Python — ele só serve arquivos estáticos. Quem executa o
script é o Actions; o Pages apenas exibe o resultado.

## Setup

1. Crie um repositório **público** no GitHub (o Actions é grátis sem limite em repo público)
   e suba estes arquivos na branch `main`.

2. Em **Settings → Pages**, defina:
   - Source: `Deploy from a branch`
   - Branch: `main`, pasta `/docs`

3. Em **Settings → Actions → General → Workflow permissions**, marque
   **Read and write permissions** (o workflow precisa commitar o `status.json`).

4. Em **Actions**, rode o workflow *Ping services* uma vez manualmente
   (`Run workflow`) para gerar os primeiros dados.

A página fica em `https://<usuario>.github.io/<repositorio>/`.

## Configurar serviços

Edite `targets.json`:

```json
{
  "targets": [
    { "name": "MyFamilySafe", "url": "https://myfamilysafe.onrender.com/health", "accept": [200] },
    { "name": "Outro", "url": "https://exemplo.onrender.com" }
  ]
}
```

- `accept` é opcional. Sem ele, qualquer resposta HTTP abaixo de 500 conta como UP —
  inclusive 404, que apenas indica que a raiz não tem rota, e não que o serviço caiu.
- Os três alvos configurados apontam para endpoints de health que devolvem `200`, então
  usam `"accept": [200]` — um 404 ou 500 ali é falha de verdade, não rota ausente.

## Rodar localmente

```bash
python scripts/ping.py
```

Sem dependências externas — só a biblioteca padrão.

## Sobre o intervalo

O cron do GitHub Actions não é pontual: em horários de pico atrasa alguns minutos, e
agendamentos muito frequentes podem ser descartados. Para manter serviços do Render
acordados (eles dormem após ~15 min sem tráfego) o intervalo de 10 minutos costuma
funcionar, mas um cold start ocasional ainda pode acontecer.
