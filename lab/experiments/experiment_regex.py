from lab.llm_requests import request_for
from lab.regex.regex_to_nfa import regex_to_nfa
from lab.automata.algorithms import nfa_to_dfa, minimize_dfa, equivalent_dfa


from lab.experiments.specs.ground_truth import ground_truth_builders
from lab.experiments.specs.prompts import REGEX_SYSTEM_PROMPT, REPAIR_PROMPTS, TEST_GENERATION_PROMPT

from lab.experiments.specs.tasks import tasks, tasks_alphabets

from lab.experiments.pipelines.repair import repair
from lab.experiments.pipelines.parallel_tests import parallel_tests


from lab.experiments.storage import regex_answer_path, save_settings, save_pipeline_artifacts

from .stats import already_saved, save_attempt, print_statistics


RUN_NAME = "regex_qwen_005"


def check_regex(
    answer: str,
    task_name: str,
) -> bool | str:
    alphabet = tasks_alphabets[task_name]

    nfa = regex_to_nfa(answer, alphabet)

    if isinstance(nfa, str):
        return nfa

    dfa = nfa_to_dfa(nfa)
    minimized_dfa = minimize_dfa(dfa)

    ground_truth = ground_truth_builders[task_name]()

    return equivalent_dfa(
        minimized_dfa,
        ground_truth,
    )


def get_regex_answers(
    model: str,
    iterations: int,
    task_name: str,
    source: str,
    pipeline: str = "single",
    draft_limit: int = -1,
    repair_limit: int = -1,
    test_limit: int = -1,
) -> tuple[float, float]:
    if pipeline not in (
        "single",
        "repair",
        "parallel_tests",
    ):
        raise ValueError(
            f"Неизвестный pipeline: {pipeline}"
        )

    if (
        pipeline in ("repair", "parallel_tests")
        and source != "local"
    ):
        raise ValueError(
            f"Pipeline {pipeline} пока поддерживает "
            "только source=local."
        )

    if pipeline == "single":
        run_name = RUN_NAME

    elif pipeline == "repair":
        run_name = (
            f"{RUN_NAME}"
            f"__repair"
            f"_d{draft_limit}"
            f"_r{repair_limit}"
        )

    else:
        run_name = (
            f"{RUN_NAME}"
            f"__parallel"
            f"_d{draft_limit}"
            f"_t{test_limit}"
            f"_r{repair_limit}"
        )

    ask = request_for(source)
    task = tasks[task_name]

    total_cost = 0.0
    total_time = 0.0

    save_regex_settings(
        model=model,
        task_name=task_name,
        source=source,
        run_name=run_name,
        pipeline=pipeline,
        draft_limit=draft_limit,
        repair_limit=repair_limit,
        test_limit=test_limit,
    )

    task_folder = regex_answer_path(
        run_name,
        source,
        model,
        task_name,
        0,
    ).parent

    for i in range(iterations):
        path = regex_answer_path(
            run_name,
            source,
            model,
            task_name,
            i,
        )

        if already_saved(path, i):
            print(
                f"{task_name}: ответ {i + 1} уже сохранён"
            )
            continue

        print(
            f"\nЗапрос: {task_name}, "
            f"ответ {i + 1}/{iterations}",
            flush=True,
        )

        info = {}

        if pipeline == "repair":
            answer, cost, elapsed = repair(
                kind="regex",
                model=model,
                task_name=task_name,
                task=task,
                draft_limit=draft_limit,
                repair_limit=repair_limit,
                metrics=info,
            )

            draft = info.get("draft", answer)

        elif pipeline == "parallel_tests":
            answer, cost, elapsed = parallel_tests(
                kind="regex",
                model=model,
                task_name=task_name,
                task=task,
                draft_limit=draft_limit,
                test_limit=test_limit,
                review_limit=repair_limit,
                metrics=info,
            )

            draft = info.get("draft", answer)

        else:
            answer, cost, elapsed = ask(
                model,
                task,
                REGEX_SYSTEM_PROMPT,
            )

            draft = answer

        if pipeline == "parallel_tests":
            artifacts_path = save_pipeline_artifacts(
                path,
                info,
            )

            print(
                "Данные pipeline сохранены в: "
                f"{artifacts_path.resolve()}"
            )

        save_attempt(
            path,
            i,
            "regex",
            task_name,
            draft,
            answer,
            elapsed,
            cost,
            info.get("repair_attempted", False),
        )

        total_cost += cost
        total_time += elapsed

        print_statistics(task_folder)

    print_statistics(
        task_folder.parent,
        recursive=True,
    )

    return total_cost, total_time


def save_regex_settings(
    model: str,
    task_name: str,
    source: str,
    *,
    run_name: str,
    pipeline: str,
    draft_limit: int,
    repair_limit: int,
    test_limit: int,
) -> None:
    folder = regex_answer_path(
        run_name,
        source,
        model,
        task_name,
        0,
    ).parent

    settings = {
        "run_name": run_name,
        "source": source,
        "model": model,
        "task_name": task_name,
        "task": tasks[task_name],
        "pipeline": pipeline,
    }

    if pipeline == "single":
        settings["system_prompt"] = REGEX_SYSTEM_PROMPT

    elif pipeline == "repair":
        draft_prompt, repair_prompt = (
            REPAIR_PROMPTS["regex"]
        )

        settings.update({
            "draft_prompt": draft_prompt,
            "repair_prompt": repair_prompt,
            "draft_limit": draft_limit,
            "repair_limit": repair_limit,
        })

    elif pipeline == "parallel_tests":
        draft_prompt, review_prompt = (
            REPAIR_PROMPTS["regex"]
        )

        settings.update({
            "draft_prompt": draft_prompt,
            "test_prompt": TEST_GENERATION_PROMPT,
            "review_prompt": review_prompt,

            "draft_limit": draft_limit,
            "test_limit": test_limit,
            "review_limit": repair_limit,

            "execution": "sequential",
            "reported_time": (
                "max(solution_branch_time, tests_time) "
                "+ review_branch_time"
            ),
        })

    save_settings(
        folder / "settings.json",
        settings,
    )