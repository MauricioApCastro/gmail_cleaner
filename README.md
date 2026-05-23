# Gmail Cleaner

Aplicativo desktop em Python/PyQt6 para conectar ao Gmail, ranquear remetentes por volume e mover e-mails selecionados para a lixeira com regras de protecao.

## Abrir no Windows

Na pasta `gmail cleaner`, use:

```powershell
.\start_gmail_cleaner.bat
```

Se voce estiver dentro da pasta `gmail_cleaner`, tambem pode usar:

```powershell
.\start_gmail_cleaner.bat
```

Ou diretamente pelo Python da venv, a partir da pasta `gmail cleaner`:

```powershell
.\.venv\Scripts\python.exe gmail_cleaner\run.py
```

## Setup do ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r gmail_cleaner\requirements.txt
```

## Credenciais do Gmail

1. No Google Cloud Console, crie um OAuth Client ID do tipo **Desktop app** com a Gmail API habilitada.
2. Baixe o JSON do OAuth Client.
3. Salve o arquivo em:

```text
gmail_cleaner\credentials\client_secret.json
```

Na primeira conexao, o navegador abre para login e consentimento do Gmail. Depois disso, o token local fica salvo em `gmail_cleaner\credentials\token.json`.

## Fluxo principal

- Conecte a conta Gmail.
- Busque um remetente manualmente ou gere o ranking por volume.
- Revise os e-mails analisados e as protecoes aplicadas.
- Confirme a limpeza para mover somente os e-mails liberados para a lixeira.

## Seguranca

Arquivos de credenciais, tokens e historicos locais sao ignorados pelo Git. Nao publique `client_secret.json`, `token.json` ou dados gerados em `src/data/`.
