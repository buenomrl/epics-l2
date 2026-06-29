import anthropic
import base64
import json
import re


def extract_bosses_from_image(image_path: str) -> list[dict]:
    client = anthropic.Anthropic()

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    media_type = media_type_map.get(ext, "image/jpeg")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Esta imagem é um tracker de epic bosses de Lineage 2. "
                            "Extraia todos os bosses com status 'Dead' que possuem janela de respawn visível. "
                            "Retorne APENAS um JSON válido, sem texto adicional, no formato:\n"
                            '[{"boss": "Queen Ant", "date": "18.06.2026", "window_start": "22:42", "window_end": "23:12"}]\n'
                            "O campo 'date' deve estar no formato DD.MM.YYYY. "
                            "Os campos 'window_start' e 'window_end' devem estar no formato HH:MM. "
                            "Inclua apenas bosses com status Dead."
                        ),
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(raw)


def _call_claude(image_path: str, prompt: str) -> str:
    client = anthropic.Anthropic()
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    media_type = media_type_map.get(ext, "image/jpeg")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return message.content[0].text.strip()


def extract_cc_members(image_path: str) -> list[str]:
    prompt = (
        "This is a Lineage 2 Command Channel Info screenshot. "
        "On the RIGHT side there is a panel titled 'Party Members' listing player names. "
        "Extract ONLY the player names from the RIGHT panel (Party Members list). "
        "Ignore the left panel (party leader list). "
        "Return ONLY a valid JSON array of strings with the exact names as shown, no extra text. "
        'Example: ["ILOVEPUSSY", "SaygoN", "MrsMagoo", "Peteco"]'
    )
    raw = _call_claude(image_path, prompt)
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(raw)
