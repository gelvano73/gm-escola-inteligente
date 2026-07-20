from __future__ import annotations

import secrets
from datetime import date

from app.services.whatsapp_client import send_whatsapp_text_sync


def senha_inicial_aluno(data_nascimento: date) -> str:
    """Compatibilidade: senha baseada na data de nascimento (DDMMAAAA)."""
    return data_nascimento.strftime("%d%m%Y")


def gerar_senha_provisoria(tamanho: int = 8) -> str:
    """Gera senha provisória aleatória (letras + dígitos, sem caracteres ambíguos)."""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def normalizar_senha_nascimento(senha: str) -> str | None:
    """Aceita DDMMAAAA, DD/MM/AAAA ou AAAA-MM-DD e devolve DDMMAAAA."""
    bruto = senha.strip()
    digitos = "".join(ch for ch in bruto if ch.isdigit())
    if len(digitos) == 8:
        try:
            d, m, y = int(digitos[0:2]), int(digitos[2:4]), int(digitos[4:8])
            date(y, m, d)
            return f"{d:02d}{m:02d}{y:04d}"
        except ValueError:
            pass
        try:
            y, m, d = int(digitos[0:4]), int(digitos[4:6]), int(digitos[6:8])
            date(y, m, d)
            return f"{d:02d}{m:02d}{y:04d}"
        except ValueError:
            return None
    return None


def entregar_senha_provisoria(
    *,
    destinatario_nome: str,
    login: str,
    senha: str,
    telefone: str | None,
    escola_nome: str = "Escola",
) -> dict:
    """
    Tenta enviar a senha provisória por WhatsApp.
    Sempre retorna o status para o admin exibir/copiar a senha na tela.
    """
    mensagem = (
        f"*{escola_nome}*\n"
        f"Olá, {destinatario_nome}!\n\n"
        f"Seu acesso ao portal foi criado/atualizado.\n"
        f"Usuário/login: *{login}*\n"
        f"Senha provisória: *{senha}*\n\n"
        f"No primeiro acesso você deverá trocar esta senha.\n"
        f"Em caso de esquecimento, entre em contato com a administração da escola."
    )
    phone = "".join(ch for ch in (telefone or "") if ch.isdigit())
    if len(phone) < 10:
        return {
            "enviado": False,
            "canal": None,
            "destino": None,
            "motivo": "Telefone não informado ou inválido. Entregue a senha manualmente.",
            "mensagem": mensagem,
        }
    try:
        result = send_whatsapp_text_sync(phone, mensagem)
        mode = result.get("mode", "whatsapp")
        return {
            "enviado": True,
            "canal": "whatsapp" if mode != "demo" else "whatsapp_demo",
            "destino": phone,
            "motivo": (
                "Mensagem registrada (WhatsApp em modo demo — configure WHATSAPP_ENABLED para envio real)."
                if mode == "demo"
                else "Senha enviada por WhatsApp."
            ),
            "mensagem": mensagem,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enviado": False,
            "canal": "whatsapp",
            "destino": phone,
            "motivo": f"Falha no envio WhatsApp: {exc}. Entregue a senha manualmente.",
            "mensagem": mensagem,
        }
