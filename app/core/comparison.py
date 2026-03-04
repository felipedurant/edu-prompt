"""Modos de comparação: v1/v2 e multi-API com geração paralela."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from app.config import (
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


def _generate_version_batch(version: str, adapter: LLMAdapter, profile: dict,
                            topic: str, generator: ContentGenerator,
                            db: Database, session_id: str,
                            results: dict, errors: dict, lock: threading.Lock,
                            completed_counter: list, total_tasks: int,
                            progress_callback):
    """Worker que processa todos os content_types para uma versão (v1 ou v2)."""
    for ct in CONTENT_TYPES:
        key = f"{ct}_{version}"
        try:
            result = generator.generate_single(adapter, profile, topic, ct, version)
            with lock:
                results[key] = result
            db.add_message(
                session_id, "assistant", result["content"],
                ct, version, result["source"],
            )
        except LLMError as e:
            with lock:
                errors[key] = str(e)
            logger.error("Falha em %s: %s", key, e)
        except Exception as e:
            with lock:
                errors[key] = str(e)
            logger.error("Erro inesperado em %s: %s", key, e)

        with lock:
            completed_counter[0] += 1
            if progress_callback:
                progress_callback(completed_counter[0], total_tasks, f"{ct} {version}")


def compare_versions(adapter: LLMAdapter, profile: dict, topic: str,
                     engine: PromptEngine, cache: CacheManager, db: Database,
                     progress_callback=None) -> dict:
    """
    Compara v1 vs v2 para todos os 4 tipos de conteúdo.
    Usa 2 threads: uma para v1, outra para v2.

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
    results = {}
    errors = {}
    lock = threading.Lock()
    completed_counter = [0]  # mutable para compartilhar entre threads
    start_total = time.time()

    # 2 threads: uma para v1 (4 content_types), outra para v2 (4 content_types)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for version in ("v1", "v2"):
            future = executor.submit(
                _generate_version_batch,
                version, adapter, profile, topic, generator,
                db, session_id, results, errors, lock,
                completed_counter, total_tasks, progress_callback,
            )
            futures.append(future)

        # Aguardar conclusão
        for future in as_completed(futures):
            future.result(timeout=300)

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


def _generate_model_batch(model_key: str, adapter: LLMAdapter, profile: dict,
                          topic: str, generator: ContentGenerator,
                          db: Database, session_id: str,
                          results: dict, errors: dict, lock: threading.Lock,
                          completed_counter: list, total_tasks: int,
                          progress_callback):
    """Worker que processa todos os content_types para um modelo."""
    label = MODEL_REGISTRY[model_key]["label"]
    for ct in CONTENT_TYPES:
        key = f"{ct}_{model_key}"
        try:
            result = generator.generate_single(
                adapter, profile, topic, ct, DEFAULT_PROMPT_VERSION,
            )
            with lock:
                results[key] = result
            db.add_message(
                session_id, "assistant", result["content"],
                ct, DEFAULT_PROMPT_VERSION, result["source"],
            )
        except LLMError as e:
            with lock:
                errors[key] = str(e)
            logger.error("Falha em %s: %s", key, e)
        except Exception as e:
            with lock:
                errors[key] = str(e)
            logger.error("Erro inesperado em %s: %s", key, e)

        with lock:
            completed_counter[0] += 1
            if progress_callback:
                progress_callback(completed_counter[0], total_tasks, f"{ct} ({label})")


def compare_models(model_keys: list[str], profile: dict, topic: str,
                   engine: PromptEngine, cache: CacheManager, db: Database,
                   progress_callback=None) -> dict:
    """
    Compara modelos selecionados para todos os 4 tipos (sempre v2).
    Usa 1 thread por modelo — cada thread processa seus content_types sequencialmente.

    Args:
        model_keys: Lista de chaves do MODEL_REGISTRY.
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
    results = {}
    errors = {}
    lock = threading.Lock()
    completed_counter = [0]
    start_total = time.time()

    # Criar adapters
    adapters = {}
    for key in model_keys:
        try:
            adapters[key] = get_adapter(key)
        except ValueError as e:
            logger.error("Não foi possível criar adapter para %s: %s", key, e)
            continue

    # 1 thread por modelo — cada thread processa 4 content_types sequencialmente
    with ThreadPoolExecutor(max_workers=len(adapters)) as executor:
        futures = []
        for model_key, adapter in adapters.items():
            future = executor.submit(
                _generate_model_batch,
                model_key, adapter, profile, topic, generator,
                db, session_id, results, errors, lock,
                completed_counter, total_tasks, progress_callback,
            )
            futures.append(future)

        # Aguardar conclusão
        for future in as_completed(futures):
            future.result(timeout=300)

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
