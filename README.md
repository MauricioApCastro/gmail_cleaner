# Gmail Cleaner

Projeto em Python para autenticar com Gmail, listar emails e preparar rotinas de limpeza.

## Setup

1. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependencias:

```powershell
pip install -r requirements.txt
```

3. No Google Cloud Console, crie um OAuth Client ID do tipo **Desktop app** com a Gmail API habilitada.

4. Baixe o arquivo JSON do OAuth Client e salve como:

```text
credentials/client_secret.json
```

Se o Windows esconder extensoes, confirme que o arquivo nao ficou como `client_secret.json.json`.

5. Execute:

```powershell
python run.py
```

Na primeira execucao, o navegador abre para login e consentimento do Gmail. Se ele nao abrir automaticamente, copie o link mostrado no terminal e abra no navegador. Depois disso, o token local fica salvo em `credentials/token.json`.

Ao executar, o script mostra:

- A tela inicial do Gmail Cleaner.
- O botao para conectar ao Gmail.
- O status da conexao.
- O botao para carregar emails.

O servico principal de leitura fica em `src/services/gmail_service.py` e expoe funcoes para listar emails, pegar assunto, remetente, data e quantidade total.

## Seguranca

Os arquivos em `credentials/` sao ignorados pelo Git para evitar vazamento de credenciais e tokens.
