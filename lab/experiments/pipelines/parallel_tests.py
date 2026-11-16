import json
import re

from lab.automata import NFA
from lab.llm_requests import local_request
from lab.regex.regex_to_nfa import regex_to_nfa

from lab.experiments.answer_parser import parse_answer
from lab.experiments.specs.ground_truth import ground_truth_builders
from lab.experiments.specs.prompts import REPAIR_PROMPTS, TEST_GENERATION_PROMPT

from lab.experiments.specs.tasks import tasks_alphabets

from .finalizer import finalize_answer


def extract_test_words(
    text: str,
    alphabet,
    max_words: int = 100
) -> list[str]:
    parsed = None
    stripped_text = text.strip()

    try:
        parsed = json.loads(stripped_text)
    except json.JSONDecodeError:
        left = stripped_text.find("[")
        right = stripped_text.rfind("]")

        if left != -1 and right > left:
            try:
                parsed = json.loads(
                    stripped_text[left:right + 1]
                )
            except json.JSONDecodeError:
                parsed = None

    if isinstance(parsed, dict):
        parsed = parsed.get("words")

    if not isinstance(parsed, list):
        parsed = []

        for match in re.finditer(
                r'"((?:\\.|[^"\\])*)"',
                stripped_text,
        ):
            try:
                word = json.loads(f'"{match.group(1)}"')
            except json.JSONDecodeError:
                continue

            parsed.append(word)

    allowed_symbols = set(alphabet)
    result = []
    used = set()

    for word in parsed:
        if not isinstance(word, str):
            continue

        if any(symbol not in allowed_symbols for symbol in word):
            continue

        if word in used:
            continue

        used.add(word)
        result.append(word)

        if len(result) >= max_words:
            break

    return result

def build_candidate(
    kind: str,
    task_name: str,
    answer: str
):
    alphabet = tasks_alphabets[task_name]

    if kind == "regex":
        nfa = regex_to_nfa(answer.strip(), alphabet)

        if isinstance(nfa, str):
            return (
                None,
                f"Ошибка формата регулярного выражения: {nfa}"
            )

        return nfa, None

    if kind == "automata" :
        parsed = parse_answer(answer)

        if isinstance(parsed, str):
            return(
                None,
                f"Ошибка формата автомата: {parsed}"
            )

        extra_letters = parsed.alphabet - set(alphabet)

        if extra_letters:
            return(
                None,
                f"Символы вне алфавита: {sorted(extra_letters)}"
            )

        nfa = NFA(
            parsed.start_states,
            alphabet,
            parsed.finish_states,
        )

        return nfa, None

    raise ValueError(
        f"Неизвестный тип эксперимента: {kind}"
    )


def build_test_report(
    kind: str,
    task_name: str,
    draft: str,
    words: list[str],
) -> tuple[str, bool]:
    ground_truth = ground_truth_builders[task_name]()

    candidate, candidate_error = build_candidate(
        kind,
        task_name,
        draft,
    )

    if not words:
        return (
            "Генератор тестов не выдал ни одного "
            "корректного тестового слова.",
            False,
        )

    failures = []
    passed = 0

    for word in words:
        expected = ground_truth.compute(word)
        shown_word = "ε" if word == "" else repr(word)

        if candidate is None:
            failures.append(
                f"{shown_word}: ожидалось {expected}, "
                "результат черновика не вычислен"
            )
            continue

        try:
            actual = candidate.compute(word)
        except Exception as exception:
            failures.append(
                f"{shown_word}: ожидалось {expected}, "
                f"при запуске произошла ошибка: {exception}"
            )
            continue

        if actual == expected:
            passed += 1
        else:
            failures.append(
                f"{shown_word}: ожидалось {expected}, "
                f"получено {actual}"
            )

    lines = [
        f"Всего тестов: {len(words)}",
        f"Пройдено: {passed}",
        f"Не пройдено: {len(failures)}",
    ]

    if candidate_error is not None:
        lines.extend([
            "",
            f"Общая ошибка ответа: {candidate_error}",
        ])

    if failures:
        lines.extend([
            "",
            "Все обнаруженные ошибки:",
        ])

        for number, failure in enumerate(failures, start=1):
            lines.append(f"{number}. {failure}")

    else:
        lines.extend([
            "",
            "Все сгенерированные тесты пройдены.",
        ])

    all_passed = (
            candidate_error is None
            and len(failures) == 0
    )

    return "\n".join(lines), all_passed


def parallel_tests(
    kind: str,
    model: str,
    task_name: str,
    task: str,
    draft_limit: int = -1,
    test_limit: int = -1,
    review_limit: int = -1,
    metrics: dict | None = None
)  -> tuple[str, float, float]:
    if kind not in ("automata", "regex"):
        raise ValueError(
            f"Неизвестный тип эксперимента: {kind}"
        )

    for limit in (
        draft_limit,
        test_limit,
        review_limit,
    ):
        if limit != -1 and limit < 1:
            raise ValueError(
                "Лимит должен быть положительным числом или -1."
            )

    if metrics is None:
        metrics = {}

    alphabet = tasks_alphabets[task_name]
    draft_prompt, review_prompt = REPAIR_PROMPTS[kind]

    draft_info = {}
    tests_info = {}
    review_info = {}

    test_task = (
        f"{task}\n\n"
        f"Алфавит: "
        f"{json.dumps(sorted(alphabet), ensure_ascii=False)}"
    )

    print("\nГенерируем решение...", flush=True)

    raw_draft, draft_generation_cost, draft_time = local_request(
        model,
        task,
        draft_prompt,
        num_predict=draft_limit,
        details=draft_info,
    )

    draft = raw_draft

    draft_finalizer_cost = 0.0
    draft_finalizer_time = 0.0

    if draft_info.get("done_reason") == "length":
        print(
            "\nЧерновик достиг лимита. "
            "Извлекаем итоговый ответ...",
            flush=True,
        )

        draft, draft_finalizer_cost, draft_finalizer_time = (
            finalize_answer(
                kind,
                model,
                task,
                thinking=draft_info.get("thinking", ""),
                partial_answer=raw_draft,
            )
        )

    solution_branch_time = (
        draft_time + draft_finalizer_time
    )

    solution_branch_cost = (
        draft_generation_cost + draft_finalizer_cost
    )

    print("\nГенерируем тестовые слова...", flush=True)

    tests_text, tests_cost, tests_time = local_request(
        model,
        test_task,
        TEST_GENERATION_PROMPT,
        num_predict=test_limit,
        details=tests_info,
    )

    words = extract_test_words(
        tests_text,
        alphabet,
    )

    print(
        f"\nПолучено корректных тестовых слов: {len(words)}",
        flush=True,
    )
    sequential_generation_time = (
        solution_branch_time + tests_time
    )

    parallel_generation_time = max(
        solution_branch_time,
        tests_time,
    )

    report, all_passed = build_test_report(
        kind,
        task_name,
        draft,
        words,
    )

    print("\nРезультаты тестирования:")
    print(report, flush=True)

    review_generation_cost = 0.0
    review_finalizer_cost = 0.0

    review_time = 0.0
    review_finalizer_time = 0.0

    raw_review_answer = ""
    review_skipped = False

    if all_passed:
        print(
            "\nВсе предложенные тесты пройдены. "
            "Сохраняем черновик без дополнительного исправления.",
            flush=True,
        )

        answer = draft
        review_skipped = True

    else:
        review_task = (
            f"Условие задачи:\n{task}\n\n"
            f"Черновик ответа:\n"
            f"{draft or '(пусто)'}\n\n"
            f"Результаты автоматического тестирования:\n"
            f"{report}\n\n"
            "В отчёте перечислены все обнаруженные неправильные "
            "результаты. Исправь каждую из найденных ошибок. "
            "Верни полный ответ в требуемом формате. "
            "Не добавляй пояснений вне требуемого формата."
        )

        print(
            "\nИсправляем решение по результатам тестов...",
            flush=True,
        )

        raw_review_answer, review_generation_cost, review_time = (
            local_request(
                model,
                review_task,
                review_prompt,
                num_predict=review_limit,
                details=review_info,
            )
        )

        answer = raw_review_answer

        if review_info.get("done_reason") == "length":
            print(
                "\nИсправление достигло лимита. "
                "Извлекаем итоговый ответ...",
                flush=True,
            )

            (
                answer,
                review_finalizer_cost,
                review_finalizer_time,
            ) = finalize_answer(
                kind,
                model,
                review_task,
                thinking=review_info.get("thinking", ""),
                partial_answer=raw_review_answer,
            )

        if not answer.strip():
            print(
                "\nПосле исправления модель не выдала ответ. "
                "Сохраняем первоначальный черновик.",
                flush=True,
            )

            answer = draft

    review_branch_time = (
            review_time + review_finalizer_time
    )

    review_branch_cost = (
            review_generation_cost + review_finalizer_cost
    )
    actual_total_time = (
            sequential_generation_time + review_branch_time
    )

    estimated_total_time = (
            parallel_generation_time + review_branch_time
    )

    total_cost = (
            solution_branch_cost
            + tests_cost
            + review_branch_cost
    )

    metrics.update({
        "pipeline": "parallel_tests",

        "raw_draft": raw_draft,
        "draft": draft,
        "draft_done_reason": draft_info.get("done_reason"),

        "generated_tests_raw": tests_text,
        "generated_tests": words,
        "tests_done_reason": tests_info.get("done_reason"),

        "test_report": report,

        "raw_review_answer": raw_review_answer,
        "final_answer": answer,
        "review_done_reason": (
            "skipped_all_tests_passed"
            if review_skipped
            else review_info.get("done_reason")
        ),

        "draft_time": draft_time,
        "draft_finalizer_time": draft_finalizer_time,
        "solution_branch_time": solution_branch_time,

        "tests_time": tests_time,

        "sequential_generation_time": (
            sequential_generation_time
        ),
        "parallel_generation_time": (
            parallel_generation_time
        ),

        "all_generated_tests_passed": all_passed,
        "review_skipped": review_skipped,

        "review_time": review_time,
        "review_finalizer_time": review_finalizer_time,
        "review_branch_time": review_branch_time,

        "actual_total_time": actual_total_time,
        "estimated_total_time": estimated_total_time,

        "total_time": estimated_total_time,

        "draft_generation_cost": draft_generation_cost,
        "draft_finalizer_cost": draft_finalizer_cost,
        "solution_branch_cost": solution_branch_cost,

        "tests_cost": tests_cost,

        "review_generation_cost": review_generation_cost,
        "review_finalizer_cost": review_finalizer_cost,
        "review_branch_cost": review_branch_cost,

        "total_cost": total_cost,

        "repair_attempted": not review_skipped,
    })

    print(
        "\nВремя последовательного запуска: "
        f"{actual_total_time:.1f} с"
    )
    print(
        "Расчётное время параллельной архитектуры: "
        f"{estimated_total_time:.1f} с"
    )

    return answer, total_cost, estimated_total_time
