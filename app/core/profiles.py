"""Gerenciamento de perfis de alunos."""

import json
import logging
from uuid import uuid4

from app.config import PROFILES_PATH, VALID_LEVELS, VALID_STYLES

logger = logging.getLogger(__name__)


def load_profiles() -> list[dict]:
    """Carrega perfis do arquivo JSON."""
    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Arquivo de perfis não encontrado: %s", PROFILES_PATH)
        return []
    except json.JSONDecodeError as e:
        logger.error("Erro ao ler perfis: %s", e)
        return []


def save_profiles(profiles: list[dict]) -> None:
    """Salva perfis no arquivo JSON."""
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)


def get_profile_by_id(profile_id: str) -> dict | None:
    """Busca perfil por ID."""
    profiles = load_profiles()
    for p in profiles:
        if p["id"] == profile_id:
            return p
    return None


def get_profile_by_index(index: int) -> dict | None:
    """Busca perfil por índice (0-based)."""
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        return profiles[index]
    return None


def validate_profile(nome: str, idade: int, nivel: str, estilo: str,
                     contexto: str = "") -> dict:
    """
    Valida e retorna um dict de perfil.

    Raises:
        ValueError: Se algum campo for inválido.
    """
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome não pode ser vazio.")
    if len(nome) > 50:
        raise ValueError("Nome deve ter no máximo 50 caracteres.")

    if not isinstance(idade, int) or idade < 5 or idade > 99:
        raise ValueError("Idade deve ser um número entre 5 e 99.")

    if nivel not in VALID_LEVELS:
        raise ValueError(f"Nível inválido. Opções: {', '.join(VALID_LEVELS)}")

    if estilo not in VALID_STYLES:
        raise ValueError(f"Estilo inválido. Opções: {', '.join(VALID_STYLES)}")

    profile_id = f"{nome.lower()}_{idade}_{nivel[:4]}_{estilo[:5]}_{uuid4().hex[:6]}"

    return {
        "id": profile_id,
        "nome": nome,
        "idade": idade,
        "nivel": nivel,
        "estilo": estilo,
        "contexto": contexto.strip(),
    }


def create_profile(nome: str, idade: int, nivel: str, estilo: str,
                   contexto: str = "", quiz_answers: list | None = None) -> dict:
    """
    Cria e persiste um novo perfil.

    Returns:
        O perfil criado.
    """
    profile = validate_profile(nome, idade, nivel, estilo, contexto)
    if quiz_answers:
        profile["quiz_answers"] = quiz_answers

    profiles = load_profiles()
    profiles.append(profile)
    save_profiles(profiles)

    logger.info("Perfil criado: %s (%s, %d anos, %s, %s)",
                profile["nome"], profile["id"], idade, nivel, estilo)
    return profile


def delete_profile(profile_id: str) -> bool:
    """Remove perfil por ID. Retorna True se removido."""
    profiles = load_profiles()
    new_profiles = [p for p in profiles if p["id"] != profile_id]
    if len(new_profiles) == len(profiles):
        return False
    save_profiles(new_profiles)
    logger.info("Perfil removido: %s", profile_id)
    return True
