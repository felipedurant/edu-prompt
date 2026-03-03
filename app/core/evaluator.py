"""LLM-as-Judge — Avaliador automático de conteúdo usando Gemini 2.5 Pro."""

import json
import logging

from app.adapters import get_judge_adapter, LLMError
from app.config import DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)

# Critérios de avaliação
EVALUATION_CRITERIA = {
    "adequacao_nivel": "Adequação ao nível — Conteúdo apropriado para a idade e nível do aluno",
    "clareza": "Clareza e coerência — Linguagem clara, lógica bem encadeada",
    "adequacao_estilo": "Adequação ao estilo — Respeita o estilo de aprendizado do perfil",
    "engajamento": "Engajamento pedagógico — Conteúdo interessante, motivador, pedagogicamente efetivo",
}

CONTENT_TYPE_LABELS = {
    "conceptual": "Explicação Conceitual",
    "practical": "Exemplos Práticos",
    "reflection": "Perguntas de Reflexão",
    "visual": "Resumo Visual",
}


class ContentEvaluator:
    """Avaliador automático de conteúdo usando Gemini 2.5 Pro como judge."""

    def __init__(self):
        self.judge = get_judge_adapter()

    def evaluate_versions(self, v1_outputs: dict, v2_outputs: dict,
                          profile: dict, topic: str) -> dict:
        """
        Compara v1 vs v2 para cada tipo de conteúdo.

        Args:
            v1_outputs: Dict[content_type, content_str]
            v2_outputs: Dict[content_type, content_str]
            profile: Perfil do aluno.
            topic: Tópico de estudo.

        Returns:
            Dict com avaliações por tipo, resumo geral e vencedor.
        """
        evaluations = {}
        total_v1 = 0
        total_v2 = 0
        count = 0

        for ct in v1_outputs:
            v1_content = v1_outputs.get(ct)
            v2_content = v2_outputs.get(ct)

            if not v1_content or not v2_content:
                continue

            label = CONTENT_TYPE_LABELS.get(ct, ct)

            system = (
                "Você é um avaliador pedagógico especializado em qualidade de conteúdo educacional. "
                "Sua tarefa é comparar duas versões de conteúdo gerado por IA e avaliar "
                "qual é mais efetiva pedagogicamente. "
                "Seja objetivo e justifique cada nota com exemplos concretos do texto avaliado."
            )

            criteria_text = "\n".join(
                f"- {name}: {desc}" for name, desc in EVALUATION_CRITERIA.items()
            )

            user = (
                f"CONTEXTO:\n"
                f"- Tópico: {topic}\n"
                f"- Tipo de conteúdo: {label}\n"
                f"- Perfil do aluno: {profile['nome']}, {profile['idade']} anos, "
                f"nível {profile['nivel']}, estilo {profile['estilo']}\n\n"
                f"VERSÃO 1 (Básica):\n{v1_content}\n\n"
                f"VERSÃO 2 (Otimizada):\n{v2_content}\n\n"
                f"TAREFA: Avalie cada versão nos seguintes critérios (nota de 1 a 10):\n"
                f"{criteria_text}\n\n"
                f"FORMATO DE RESPOSTA (JSON estrito):\n"
                f'{{\n'
                f'  "v1_scores": {{\n'
                f'    "adequacao_nivel": <1-10>,\n'
                f'    "clareza": <1-10>,\n'
                f'    "adequacao_estilo": <1-10>,\n'
                f'    "engajamento": <1-10>\n'
                f'  }},\n'
                f'  "v2_scores": {{\n'
                f'    "adequacao_nivel": <1-10>,\n'
                f'    "clareza": <1-10>,\n'
                f'    "adequacao_estilo": <1-10>,\n'
                f'    "engajamento": <1-10>\n'
                f'  }},\n'
                f'  "justificativa": "<2-3 frases comparando as versões>",\n'
                f'  "vencedor": "v1" ou "v2"\n'
                f'}}\n\n'
                f"Responda APENAS com o JSON, sem texto adicional."
            )

            try:
                response = self.judge.generate(
                    messages=[{"role": "user", "content": user}],
                    system_prompt=system,
                    temperature=0.3,
                )
                evaluation = self._parse_evaluation(response)
                evaluations[ct] = {
                    "label": label,
                    **evaluation,
                }

                v1_avg = sum(evaluation["v1_scores"].values()) / len(evaluation["v1_scores"])
                v2_avg = sum(evaluation["v2_scores"].values()) / len(evaluation["v2_scores"])
                total_v1 += v1_avg
                total_v2 += v2_avg
                count += 1

            except LLMError as e:
                logger.error("Falha na avaliação de %s: %s", ct, e)
                evaluations[ct] = {"label": label, "error": str(e)}
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Resposta do judge inválida para %s: %s", ct, e)
                evaluations[ct] = {"label": label, "error": f"Resposta inválida: {e}"}

        overall_winner = None
        if count > 0:
            avg_v1 = total_v1 / count
            avg_v2 = total_v2 / count
            overall_winner = "v2" if avg_v2 >= avg_v1 else "v1"

        return {
            "evaluations": evaluations,
            "overall_winner": overall_winner,
            "overall_v1_avg": round(total_v1 / count, 1) if count else 0,
            "overall_v2_avg": round(total_v2 / count, 1) if count else 0,
            "evaluation_type": "version_comparison",
            "evaluator_model": self.judge.get_model_name(),
        }

    def evaluate_apis(self, api_outputs: dict[str, dict],
                      profile: dict, topic: str) -> dict:
        """
        Compara outputs de diferentes APIs para cada tipo de conteúdo.

        Args:
            api_outputs: Dict[content_type, Dict[model_key, content_str]]
            profile: Perfil do aluno.
            topic: Tópico de estudo.

        Returns:
            Dict com avaliações por tipo, scores por modelo e vencedor geral.
        """
        evaluations = {}
        model_totals: dict[str, float] = {}
        model_counts: dict[str, int] = {}

        for ct, models_content in api_outputs.items():
            if len(models_content) < 2:
                continue

            label = CONTENT_TYPE_LABELS.get(ct, ct)

            system = (
                "Você é um avaliador pedagógico especializado em qualidade de conteúdo educacional. "
                "Sua tarefa é comparar conteúdos gerados por diferentes modelos de IA e avaliar "
                "qual é mais efetivo pedagogicamente. "
                "Seja objetivo e justifique cada nota."
            )

            models_text = ""
            model_keys = list(models_content.keys())
            for mk in model_keys:
                models_text += f"\n--- MODELO: {mk} ---\n{models_content[mk]}\n"

            criteria_text = "\n".join(
                f"- {name}: {desc}" for name, desc in EVALUATION_CRITERIA.items()
            )

            scores_template = {}
            for mk in model_keys:
                scores_template[mk] = {
                    "adequacao_nivel": "<1-10>",
                    "clareza": "<1-10>",
                    "adequacao_estilo": "<1-10>",
                    "engajamento": "<1-10>",
                }

            user = (
                f"CONTEXTO:\n"
                f"- Tópico: {topic}\n"
                f"- Tipo de conteúdo: {label}\n"
                f"- Perfil do aluno: {profile['nome']}, {profile['idade']} anos, "
                f"nível {profile['nivel']}, estilo {profile['estilo']}\n\n"
                f"CONTEÚDOS A AVALIAR:\n{models_text}\n\n"
                f"TAREFA: Avalie cada modelo nos seguintes critérios (nota de 1 a 10):\n"
                f"{criteria_text}\n\n"
                f"FORMATO DE RESPOSTA (JSON estrito):\n"
                f'{{\n'
                f'  "scores": {json.dumps(scores_template, indent=2)},\n'
                f'  "justificativa": "<2-3 frases comparando os modelos>",\n'
                f'  "vencedor": "<model_key do melhor>"\n'
                f'}}\n\n'
                f"Responda APENAS com o JSON, sem texto adicional."
            )

            try:
                response = self.judge.generate(
                    messages=[{"role": "user", "content": user}],
                    system_prompt=system,
                    temperature=0.3,
                )
                evaluation = self._parse_api_evaluation(response, model_keys)
                evaluations[ct] = {"label": label, **evaluation}

                for mk in model_keys:
                    if mk in evaluation.get("scores", {}):
                        avg = sum(evaluation["scores"][mk].values()) / len(evaluation["scores"][mk])
                        model_totals[mk] = model_totals.get(mk, 0) + avg
                        model_counts[mk] = model_counts.get(mk, 0) + 1

            except LLMError as e:
                logger.error("Falha na avaliação de %s: %s", ct, e)
                evaluations[ct] = {"label": label, "error": str(e)}
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Resposta do judge inválida para %s: %s", ct, e)
                evaluations[ct] = {"label": label, "error": f"Resposta inválida: {e}"}

        # Calcular médias e vencedor
        model_averages = {}
        for mk in model_totals:
            if model_counts.get(mk, 0) > 0:
                model_averages[mk] = round(model_totals[mk] / model_counts[mk], 1)

        overall_winner = max(model_averages, key=model_averages.get) if model_averages else None

        return {
            "evaluations": evaluations,
            "model_averages": model_averages,
            "overall_winner": overall_winner,
            "evaluation_type": "api_comparison",
            "evaluator_model": self.judge.get_model_name(),
        }

    @staticmethod
    def _parse_evaluation(response: str) -> dict:
        """Extrai JSON de avaliação v1/v2 da resposta do judge."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)

        for version_key in ("v1_scores", "v2_scores"):
            scores = data[version_key]
            for criterion in EVALUATION_CRITERIA:
                val = scores[criterion]
                scores[criterion] = max(1, min(10, int(val)))

        return {
            "v1_scores": data["v1_scores"],
            "v2_scores": data["v2_scores"],
            "justificativa": data.get("justificativa", ""),
            "vencedor": data.get("vencedor", ""),
        }

    @staticmethod
    def _parse_api_evaluation(response: str, model_keys: list[str]) -> dict:
        """Extrai JSON de avaliação multi-API da resposta do judge."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)

        scores = data.get("scores", {})
        for mk in model_keys:
            if mk in scores:
                for criterion in EVALUATION_CRITERIA:
                    if criterion in scores[mk]:
                        scores[mk][criterion] = max(1, min(10, int(scores[mk][criterion])))

        return {
            "scores": scores,
            "justificativa": data.get("justificativa", ""),
            "vencedor": data.get("vencedor", ""),
        }
