from __future__ import annotations


def buscar_emails_por_remetente(service, remetente: str) -> list[str]:
    remetente = remetente.strip()
    if not remetente:
        raise ValueError("Informe um remetente para buscar.")

    message_ids = []
    page_token = None

    while True:
        request_params = {
            "userId": "me",
            "q": f"from:{remetente}",
            "maxResults": 500,
        }
        if page_token:
            request_params["pageToken"] = page_token

        request = (
            service.users()
            .messages()
            .list(**request_params)
        )
        response = request.execute()
        message_ids.extend(
            message["id"] for message in response.get("messages", [])
        )
        print(f"Encontrados ate agora: {len(message_ids)}")

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return message_ids


def mover_emails_para_lixeira(service, message_ids: list[str]) -> int:
    total = len(message_ids)

    for index, message_id in enumerate(message_ids, start=1):
        print(f"Movendo {index}/{total} para a lixeira...")
        service.users().messages().trash(userId="me", id=message_id).execute()

    return total
