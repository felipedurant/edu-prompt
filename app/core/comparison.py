"""Modos de comparação: v1/v2 e multi-API com geração paralela."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from app.config import (
    MAX_PARALLEL_WORKERS,
    DEFAULT_PROMPT_VERSION,
    DEFAULT_TEMPERATURE,
    CONTENT_TYPES,
    MODEL_REGISTRY,
)
from app.adapters import get_adapter, LLMError
from app.adapters.base import LLMAdapter
from app.core.prompt_engine import PromptEngine
from app.core.content_generator import ContentGenerator
from app.storage.cache import CacheManager
from app.storage.database import Database

logger = logging.getLogger(__name__)

# Labels para exibição
CONTENT_TYPE_LABELS = {
    "conceptual": "Explicação Conceitual",
    "practical": "Exemplos Práticos",
    "reflection": "Perguntas de Reflexão",
    "visual": "Resumo Visual",
}

def compare_versions(adapter: LLMAdapter, profile: dict, topic: str,
                     engine: PromptEngine, cache: CacheManager, db: Database,
                     progress_callback=None) -> dict:
    """
    Compara v1 vs v2 para todos os 4 tipos de conteúdo.

    Args:
        progress_callback: Callable(completed, total, description) para progress bar.

    Returns:
        Dict com 'results' (por tipo), 'session_id', 'cache_stats', 'total_elapsed'.
    """
    session_id = str(uuid4())
    provider = adapter.get_provider_name()
    model = adapter.get_model_name()

    db.save_profile(profile)
    db.create_session(
        session_id=session_id,
        profile_id=profile["id"],
        provider=provider,
        model=model,
        topic=topic,
        mode="compare_versions",
    )

    generator = ContentGenerator(engine, cache)
    total_tasks = len(CONTENT_TYPES) * 2  # 4 tipos × 2 versões = 8
    completed = 0
    results = {}
    errors = {}
    start_total = time.time()

    # Preparar tarefas
    tasks = []
    for ct in CONTENT_TYPES:
        for version in ("v1", "v2"):
            tasks.append({
                "key": f"{ct}_{version}",
                "content_type": ct,
                "version": version,
            })

    # Executar em paralelo
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        future_to_key = {}
        for task in tasks:
            future = executor.submit(
                generator.generate_single,
                adapter, profile, topic, task["content_type"], task["version"],
            )
            future_to_key[future] = task

        for future in as_completed(future_to_key):
            task = future_to_key[future]
            key = task["key"]
            try:
                result = future.result(timeout=100)
                results[key] = result
                # Salva no DB
                db.add_message(
                    session_id, "assistant", result["content"],
                    task["content_type"], task["version"], result["source"],
                )
            except LLMError as e:
                errors[key] = str(e)
                logger.error("Falha em %s: %s", key, e)
            except Exception as e:
                errors[key] = str(e)
                logger.error("Erro inesperado em %s: %s", key, e)

            completed += 1
            if progress_callback:
                progress_callback(completed, total_tasks, f"{task['content_type']} {task['version']}")

    total_elapsed = round(time.time() - start_total, 1)

    # Organizar resultados por tipo
    organized = {}
    for ct in CONTENT_TYPES:
        organized[ct] = {
            "label": CONTENT_TYPE_LABELS[ct],
            "v1": results.get(f"{ct}_v1"),
            "v2": results.get(f"{ct}_v2"),
            "v1_error": errors.get(f"{ct}_v1"),
            "v2_error": errors.get(f"{ct}_v2"),
        }

    db.end_session(session_id)

    return {
        "results": organized,
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "profile": profile,
        "topic": topic,
        "cache_stats": cache.get_stats(),
        "total_elapsed": total_elapsed,
        "errors": errors,
    }


def compare_models(model_keys: list[str], profile: dict, topic: str,
                   engine: PromptEngine, cache: CacheManager, db: Database,
                   progress_callback=None) -> dict:
    """
    Compara modelos selecionados (1 por provedor) para todos os 4 tipos (sempre v2).

    Args:
        model_keys: Lista de chaves do MODEL_REGISTRY (ex: ["gemini-flash", "llama4-scout", "kimi-k2.5"]).
        progress_callback: Callable(completed, total, description) para progress bar.

    Returns:
        Dict com 'results' (por tipo por modelo), 'session_id', 'cache_stats', 'total_elapsed'.
    """
    if not model_keys:
        raise ValueError("Nenhum modelo selecionado.")

    session_id = str(uuid4())
    db.save_profile(profile)
    db.create_session(
        session_id=session_id,
        profile_id=profile["id"],
        provider=",".join(model_keys),
        model="multi",
        topic=topic,
        mode="compare_apis",
    )

    generator = ContentGenerator(engine, cache)
    total_tasks = len(CONTENT_TYPES) * len(model_keys)
    completed = 0
    results = {}
    errors = {}
    start_total = time.time()

    # Criar adapters
    adapters = {}
    for key in model_keys:
        try:
            adapters[key] = get_adapter(key)
        except ValueError as e:
            logger.error("Não foi possível criar adapter para %s: %s", key, e)
            continue

    # Preparar tarefas
    tasks = []
    for ct in CONTENT_TYPES:
        for model_key, adapter in adapters.items():
            tasks.append({
                "key": f"{ct}_{model_key}",
                "content_type": ct,
                "model_key": model_key,
                "adapter": adapter,
            })

    # Executar em paralelo
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        future_to_key = {}
        for task in tasks:
            future = executor.submit(
                generator.generate_single,
                task["adapter"], profile, topic,
                task["content_type"], DEFAULT_PROMPT_VERSION,
            )
            future_to_key[future] = task

        for future in as_completed(future_to_key):
            task = future_to_key[future]
            key = task["key"]
            try:
                result = future.result(timeout=100)
                results[key] = result
                db.add_message(
                    session_id, "assistant", result["content"],
                    task["content_type"], DEFAULT_PROMPT_VERSION, result["source"],
                )
            except LLMError as e:
                errors[key] = str(e)
                logger.error("Falha em %s: %s", key, e)
            except Exception as e:
                errors[key] = str(e)
                logger.error("Erro inesperado em %s: %s", key, e)

            completed += 1
            if progress_callback:
                label = MODEL_REGISTRY[task["model_key"]]["label"]
                progress_callback(completed, total_tasks, f"{task['content_type']} ({label})")

    total_elapsed = round(time.time() - start_total, 1)

    # Organizar resultados por tipo
    organized = {}
    for ct in CONTENT_TYPES:
        models_data = {}
        for model_key in adapters:
            key = f"{ct}_{model_key}"
            models_data[model_key] = {
                "result": results.get(key),
                "error": errors.get(key),
                "label": MODEL_REGISTRY[model_key]["label"],
            }
        organized[ct] = {
            "label": CONTENT_TYPE_LABELS[ct],
            "models": models_data,
        }

    db.end_session(session_id)

    return {
        "results": organized,
        "session_id": session_id,
        "model_keys": list(adapters.keys()),
        "profile": profile,
        "topic": topic,
        "cache_stats": cache.get_stats(),
        "total_elapsed": total_elapsed,
        "errors": errors,
    }
