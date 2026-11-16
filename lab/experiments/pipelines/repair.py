from time import perf_counter


from lab.automata import NFA
from lab.llm_requests import local_request
from lab.regex.regex_to_nfa import regex_to_nfa

from lab.experiments.answer_parser import parse_answer
from lab.experiments.specs.tasks import tasks_alphabets, tasks_tests

from lab.experiments.specs.prompts import REPAIR_PROMPTS

from .finalizer import finalize_answer

def first_issue(kind : str, task_name : str, answer : str) -> str | None :
    if not answer.strip() :
        return "Модель не выдала итоговый ответ."

    alphabet = tasks_alphabets[task_name]

    if kind == "regex" :
        nfa = regex_to_nfa(answer, alphabet)
        if isinstance(nfa,str) :
            return f"Ошибка формата регулярного выражения: {nfa}."

    elif kind == "automata" :
        parsed = parse_answer(answer)
        if isinstance(parsed, str) :
            return f"Ошибка формата автомата: {parsed}."

        extra_letters = parsed.alphabet - set(alphabet)
        if extra_letters:
            return f"Символы вне алфавита: {sorted(extra_letters)}."

        nfa = NFA(parsed.start_states, alphabet, parsed.finish_states)

    else :
        raise ValueError(f"Неизвестный тип эксперимента: {kind}")

    for word, expected in tasks_tests[task_name].items() :
        actual = nfa.compute(word)
        if actual != expected :
            return (
                f"На слове {word!r} ожидалось {expected}, "
                f"но ответ даёт {actual}"
            )

    return None

def repair(
    kind: str,
    model: str,
    task_name: str,
    task: str,
    draft_limit: int = -1,
    repair_limit: int = -1,
    metrics: dict | None = None
) -> tuple[str, float, float]:
    if kind not in ("automata", "regex") :
        raise ValueError(f"Неизвестный тип эксперимента: {kind}")

    for limit in (draft_limit, repair_limit):
        if limit != -1 and limit < 1:
            raise ValueError("Лимит должен быть положительным числом или -1.")

    started = perf_counter()
    draft_prompt, repair_prompt = REPAIR_PROMPTS[kind]

    draft_info = {}

    draft, total_cost, _ = local_request(
        model,
        task,
        draft_prompt,
        num_predict=draft_limit,
        details=draft_info
    )

    if draft_info.get("done_reason") == "length":
        print("\nЧерновик достиг лимита.", flush=True)

        draft, cost, _ = finalize_answer(
            kind,
            model,
            task,
            thinking=draft_info.get("thinking", ""),
            partial_answer=draft
        )
        total_cost += cost

    if metrics is not None:
        metrics["draft"] = draft
        metrics["repair_attempted"] = False
    if not draft.strip():
        print("Не удалось получить итоговый черновик.", flush=True)
        return "", total_cost, perf_counter() - started

    answer = draft

    issue = first_issue(kind, task_name, draft)

    if issue is not None:
        print(f"Пробуем исправить: {issue}", flush=True)

        if metrics is not None:
            metrics["repair_attempted"] = True

        repair_task = (
            f"{task}\n\n"
            f"Предыдущий ответ:\n{draft or '(пусто)'}\n\n"
            f"Ошибка проверки: {issue}\n"
            "Исправь ошибку. Верни полный ответ в требуемом формате."
        )

        repair_info = {}

        candidate, cost, _ = local_request(
            model,
            repair_task,
            repair_prompt,
            num_predict=repair_limit,
            details=repair_info
        )
        total_cost += cost

        if repair_info.get("done_reason") == "length":
            print("\nПравка достигла лимита.", flush=True)

            candidate, cost, _ = finalize_answer(
                kind,
                model,
                repair_task,
                thinking=repair_info.get("thinking", ""),
                partial_answer=candidate
            )
            total_cost += cost

        issue_after_repair = first_issue(kind, task_name, candidate)

        if issue_after_repair is None:
            answer = candidate
        else:
            print(
                f"Правка не прошла проверку: {issue_after_repair} "
                "Сохраняем черновик.",
                flush=True
            )

    return answer, total_cost, perf_counter() - started
