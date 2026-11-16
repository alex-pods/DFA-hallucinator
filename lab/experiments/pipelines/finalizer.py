from lab.llm_requests import local_request

from lab.experiments.specs.prompts import FINALIZE_PROMPTS


FINALIZE_LIMIT = 1024
THINKING_TAIL_CHARS = 12000


def finalize_answer(
    kind : str,
    model : str,
    task : str,
    thinking : str,
    partial_answer : str = "",
    *,
    limit : int = FINALIZE_LIMIT
) -> tuple[str, float, float] :

    if kind not in FINALIZE_PROMPTS :
        raise ValueError(f"Неизвестный тип эксперимента: {kind}")

    if limit < 1 :
        raise ValueError("Лимит итогового ответа должен быть положительным.")

    if not thinking.strip() and not partial_answer.strip() :
        print("Нет рассуждений или текста ответа для оформления.", flush=True)
        return "", 0.0, 0.0

    final_task = (
        f"Условие задачи:\n{task}\n\n"
        f"Конец предыдущих рассуждений:\n{thinking[-THINKING_TAIL_CHARS:]}\n\n"
        f"Начатый итоговый ответ:\n{partial_answer or '(отсутствует)'}"
    )

    print("\nОформляем ответ по рассуждениям...", flush=True)

    info = {}

    answer, cost, elapsed = local_request(
        model,
        final_task,
        FINALIZE_PROMPTS[kind],
        num_predict=limit,
        think=False,
        details=info
    )

    if info.get("done_reason") != "stop" :
        print("Оформление ответа не завершилось.", flush=True)
        return "", cost, elapsed

    return answer, cost, elapsed