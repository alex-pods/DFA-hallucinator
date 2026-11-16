import argparse
import json
from pathlib import Path
from lab.experiments.stats import checked_correct


EXPERIMENT_ROOTS = {
    "automata": Path("experiments"),
    "regex": Path("regex_experiments"),
}


def load_attempts(
    task_folder: Path,
    experiment: str,
    task_name: str,
) -> dict:
    statistics_path = task_folder / "statistics.json"

    attempts = {}

    if statistics_path.exists():
        data = json.loads(
            statistics_path.read_text(encoding="utf-8")
        )

        attempts.update(data.get("attempts", {}))

    for answer_path in sorted(task_folder.glob("*.txt")):
        suffix = answer_path.stem.rsplit("__", 1)[-1]

        if suffix.isdigit():
            number = str(int(suffix))
        else:
            number = f"file:{answer_path.name}"

        if number in attempts:
            continue

        answer = answer_path.read_text(encoding="utf-8")

        attempts[number] = {
            "draft": None,
            "answer": answer,
            "draft_correct": None,
            "final_correct": checked_correct(
                experiment,
                task_name,
                answer,
            ),
            "repair_attempted": None,
            "elapsed": None,
            "cost": None,
            "legacy": True,
        }

    return attempts

def numeric_value(value) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    return None


def format_number(
    total: float,
    known: int,
    attempts: int,
    suffix: str = "",
    prefix: str = "",
) -> str:
    if known == 0:
        return "—"

    result = f"{prefix}{total:.1f}{suffix}"

    if known < attempts:
        result += "+?"

    return result


def load_actual_times(task_folder: Path) -> dict[str, float]:
    result = {}

    for path in task_folder.glob("*__pipeline.json"):
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            continue

        stem = path.stem

        if not stem.endswith("__pipeline"):
            continue

        answer_stem = stem.removesuffix("__pipeline")
        number_text = answer_stem.rsplit("__", 1)[-1]

        if not number_text.isdigit():
            continue

        number = str(int(number_text))

        actual_time = data.get("actual_total_time")

        if isinstance(actual_time, (int, float)):
            result[number] = float(actual_time)

    return result


def rate(records: list[dict], field: str) -> str:
    checked = [
        record.get(field)
        for record in records
        if record.get(field) is not None
    ]

    if not checked:
        return "—"

    correct = sum(value is True for value in checked)
    percent = 100 * correct / len(checked)

    return f"{correct}/{len(checked)} ({percent:.1f}%)"


def fixed_count(records: list[dict]) -> str:
    comparable = [
        record
        for record in records
        if record.get("draft_correct") is not None
        and record.get("final_correct") is not None
    ]

    if not comparable:
        return "—"

    count = sum(
        record.get("draft_correct") is False
        and record.get("final_correct") is True
        for record in comparable
    )

    return str(count)



def broken_count(records: list[dict]) -> str:
    comparable = [
        record
        for record in records
        if record.get("draft_correct") is not None
        and record.get("final_correct") is not None
    ]

    if not comparable:
        return "—"

    count = sum(
        record.get("draft_correct") is True
        and record.get("final_correct") is False
        for record in comparable
    )

    return str(count)


def pipeline_name(run_name: str) -> str:
    if "__parallel" in run_name:
        return "parallel_tests"

    if "__repair" in run_name:
        return "repair"

    return "single"


def format_table(
    headers: list[str],
    rows: list[list[str]],
) -> None:
    widths = []

    for column, header in enumerate(headers):
        width = len(header)

        for row in rows:
            width = max(width, len(row[column]))

        widths.append(width)

    header_line = " | ".join(
        header.ljust(widths[i])
        for i, header in enumerate(headers)
    )

    separator = "-+-".join(
        "-" * width
        for width in widths
    )

    print(header_line)
    print(separator)

    for row in rows:
        print(
            " | ".join(
                value.ljust(widths[i])
                for i, value in enumerate(row)
            )
        )


def collect_task_result(
    experiment: str,
    model_name: str,
    task_name: str,
    task_folder: Path,
) -> tuple[
    list[str],
    list[dict],
    float,
    int,
    float,
    int,
    float,
    int,
]:
    attempts = load_attempts(
        task_folder,
        experiment,
        task_name,
    )

    actual_times = load_actual_times(task_folder)
    records = list(attempts.values())

    reported_time = 0.0
    reported_known = 0

    actual_time = 0.0
    actual_known = 0

    total_cost = 0.0
    cost_known = 0

    for number, record in attempts.items():
        elapsed = numeric_value(record.get("elapsed"))
        cost = numeric_value(record.get("cost"))

        if elapsed is not None:
            reported_time += elapsed
            reported_known += 1

        pipeline_actual_time = actual_times.get(number)

        if pipeline_actual_time is not None:
            actual_time += pipeline_actual_time
            actual_known += 1

        elif elapsed is not None:
            actual_time += elapsed
            actual_known += 1

        if cost is not None:
            total_cost += cost
            cost_known += 1

    attempts_count = len(records)

    row = [
        model_name,
        task_name,
        str(attempts_count),
        rate(records, "draft_correct"),
        rate(records, "final_correct"),
        fixed_count(records),
        broken_count(records),
        format_number(
            reported_time,
            reported_known,
            attempts_count,
            suffix=" с",
        ),
        format_number(
            actual_time,
            actual_known,
            attempts_count,
            suffix=" с",
        ),
        (
            "—"
            if cost_known == 0
            else (
                f"${total_cost:.6f}"
                + ("+?" if cost_known < attempts_count else "")
            )
        ),
    ]

    return (
        row,
        records,
        reported_time,
        reported_known,
        actual_time,
        actual_known,
        total_cost,
        cost_known,
    )

def print_run_results(
    experiment: str,
    run_name: str,
    run_root: Path,
    source: str,
) -> bool:
    rows = []
    all_records = []

    total_reported_time = 0.0
    total_reported_known = 0

    total_actual_time = 0.0
    total_actual_known = 0

    total_cost = 0.0
    total_cost_known = 0

    if not run_root.exists():
        return False

    for model_folder in sorted(run_root.iterdir()):
        if not model_folder.is_dir():
            continue

        for task_folder in sorted(model_folder.iterdir()):
            if not task_folder.is_dir():
                continue

            attempts = load_attempts(
                task_folder,
                experiment,
                task_folder.name,
            )

            if not attempts:
                continue

            (
                row,
                records,
                reported_time,
                reported_known,
                actual_time,
                actual_known,
                cost,
                cost_known,
            ) = collect_task_result(
                experiment,
                model_folder.name,
                task_folder.name,
                task_folder,
            )

            rows.append(row)
            all_records.extend(records)

            total_reported_time += reported_time
            total_reported_known += reported_known

            total_actual_time += actual_time
            total_actual_known += actual_known

            total_cost += cost
            total_cost_known += cost_known

    if not rows:
        return False

    attempts_count = len(all_records)

    if total_cost_known == 0:
        cost_text = "—"
    else:
        cost_text = f"${total_cost:.6f}"

        if total_cost_known < attempts_count:
            cost_text += "+?"

    rows.append([
        "ИТОГО",
        "все задачи",
        str(attempts_count),
        rate(all_records, "draft_correct"),
        rate(all_records, "final_correct"),
        fixed_count(all_records),
        broken_count(all_records),
        format_number(
            total_reported_time,
            total_reported_known,
            attempts_count,
            suffix=" с",
        ),
        format_number(
            total_actual_time,
            total_actual_known,
            attempts_count,
            suffix=" с",
        ),
        cost_text,
    ])

    print("\n================================================")
    print(f"Запуск: {run_name}")
    print(f"Pipeline: {pipeline_name(run_name)}")
    print(f"Источник: {source}")
    print("================================================")

    format_table(
        [
            "Модель",
            "Задача",
            "Попыток",
            "Черновики",
            "Итоговые",
            "Исправлено",
            "Испорчено",
            "Расч. время",
            "Факт. время",
            "Стоимость",
        ],
        rows,
    )

    legacy_count = sum(
        record.get("legacy") is True
        for record in all_records
    )

    if legacy_count:
        print(
            f"\nСтарых ответов без statistics.json: "
            f"{legacy_count}"
        )
        print(
            "Для них известна только правильность "
            "итогового ответа."
        )

    return True


def find_runs(
    root: Path,
    base_run_name: str,
) -> list[Path]:
    if not root.exists():
        return []

    result = []

    for path in root.iterdir():
        if not path.is_dir():
            continue

        if (
            path.name == base_run_name
            or path.name.startswith(base_run_name + "__")
        ):
            result.append(path)

    return sorted(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Показывает результаты single, repair и "
            "parallel_tests по базовому имени запуска."
        )
    )

    parser.add_argument(
        "experiment",
        choices=EXPERIMENT_ROOTS,
    )

    parser.add_argument(
        "run_name",
        help=(
            "Базовое имя запуска, например regex_qwen_004. "
            "Также будут найдены его __repair и __parallel варианты."
        ),
    )

    parser.add_argument(
        "--source",
        choices=("local", "openrouter"),
        help=(
            "Если не указан, результаты ищутся "
            "для обоих источников."
        ),
    )

    args = parser.parse_args()

    root = EXPERIMENT_ROOTS[args.experiment]
    runs = find_runs(root, args.run_name)

    if not runs:
        raise SystemExit(
            f"Не найдены запуски с именем {args.run_name!r} "
            f"в папке {root}."
        )

    sources = (
        [args.source]
        if args.source
        else ["local", "openrouter"]
    )

    found_results = False

    for run_path in runs:
        for source in sources:
            source_root = run_path / source

            if not source_root.exists():
                continue

            printed = print_run_results(
                args.experiment,
                run_path.name,
                source_root,
                source,
            )

            if printed:
                found_results = True

    if not found_results:
        raise SystemExit(
            "Папки запусков найдены, но statistics.json "
            "для указанного источника отсутствуют."
        )


if __name__ == "__main__":
    main()