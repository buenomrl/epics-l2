<div align="center">
  <h1>⚔️ Epics — L2 Boss Tracker</h1>
  <p>Gerenciador de Epic Bosses e presença de guild para Lineage 2</p>

  <a href="https://discord-sheets-app.vercel.app">
    <img src="https://img.shields.io/badge/demo-live-brightgreen?style=for-the-badge" alt="Live Demo" />
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3-black?style=for-the-badge&logo=flask" />
  <img src="https://img.shields.io/badge/Claude_AI-Vision-FF6B35?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Google_Sheets-API-34A853?style=for-the-badge&logo=google-sheets&logoColor=white" />
  <img src="https://img.shields.io/badge/Discord-Webhook-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
</div>

---

## O que é

**Epics** é uma ferramenta web interna para guilds de **Lineage 2** com dois fluxos principais movidos a IA:

### Boss Tracker → Discord

Envie uma screenshot do rastreador de epics. A IA (Claude Vision) identifica quais bosses estão **Dead** com a janela de respawn e gera uma mensagem formatada pronta para postar no Discord ou WhatsApp.

### CC Tracker → Google Sheets

Envie screenshots do Command Channel após um boss kill. A IA extrai os membros presentes, cruza com a lista de CPs da guild via **matching fuzzy** e registra a presença automaticamente na planilha — com histórico, resumo por CP e estatísticas individuais.

---

## Stack

| Componente | Tech |
|------------|------|
| Backend | Python 3 + Flask |
| IA (OCR / Visão) | Claude claude-sonnet-4-6 (Anthropic API) |
| Planilha | Google Sheets API via `gspread` |
| Notificações | Discord Webhooks |
| Frontend | HTML + Jinja2 + Vanilla JS |

---

## Configuração

### 1. Clone e instale

```bash
git clone https://github.com/buenomrl/epics-l2.git
cd epics-l2/discord-sheets-app
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 2. Configure o `.env`

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais — veja [Variáveis de ambiente](#variáveis-de-ambiente).

### 3. Credenciais do Google _(apenas para CC Tracker)_

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com)
2. Ative a **Google Sheets API**
3. Crie uma **Service Account** e baixe o JSON
4. Salve o JSON em `discord-sheets-app/credentials.json`
5. Compartilhe a planilha com o e-mail da service account

### 4. Lista de CPs

Edite o arquivo `CP List.txt` na raiz do projeto com o formato:

```
NomeDaCP1
* Membro1
* Membro2

NomeDaCP2
* Membro3
* Membro4
```

### 5. Inicie

```bash
# Linux/macOS
python app.py

# Windows
start.bat
```

Acesse [http://localhost:5000](http://localhost:5000).

---

## Variáveis de ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|:-----------:|
| `ANTHROPIC_API_KEY` | API Key da Anthropic (Claude) | Sim |
| `DISCORD_WEBHOOK_URL` | Webhook do canal Discord | Sim |
| `GOOGLE_SHEETS_ID` | ID da planilha Google Sheets | CC Tracker |
| `GOOGLE_CREDENTIALS_PATH` | Caminho para o `credentials.json` | CC Tracker |
| `CP_LIST_PATH` | Caminho alternativo para `CP List.txt` | Não |

---

## Estrutura

```
epics-l2/
├── CP List.txt                   # Mapeamento membro → CP da guild
├── Exemplo.JPG                   # Screenshot de exemplo (Boss Tracker)
├── ExemploCC.JPG                 # Screenshot de exemplo (CC Tracker)
└── discord-sheets-app/
    ├── app.py                    # Flask — rotas e lógica principal
    ├── requirements.txt
    ├── .env.example
    ├── start.bat                 # Launcher Windows
    ├── services/
    │   ├── claude_vision.py      # Extração de dados via Claude Vision
    │   ├── discord_sender.py     # Formatação e envio para Discord
    │   ├── cp_tracker.py         # Matching fuzzy de nomes de membros
    │   └── sheets_writer.py      # Escrita no Google Sheets
    └── templates/
        └── index.html            # UI single-page
```

---

## Rotas da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Interface principal |
| `POST` | `/preview` | Extrai bosses de uma imagem e gera mensagem |
| `POST` | `/send` | Envia mensagem para o Discord |
| `POST` | `/process-cc` | Processa screenshots de CC e identifica membros |
| `POST` | `/save-attendance` | Salva presença no Google Sheets |

---

## Deploy

Hospedado na Vercel: **[discord-sheets-app.vercel.app](https://discord-sheets-app.vercel.app)**

> As funcionalidades requerem as variáveis de ambiente configuradas no painel da Vercel.
