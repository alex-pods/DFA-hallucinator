import json
from pathlib import Path

from lab.automata import NFA
from lab.automata.algorithms import nfa_to_dfa, equivalent_dfa
from lab.regex.regex_to_nfa import regex_to_nfa

from .answer_parser import parse_answer
from .specs.tasks import tasks_alphabets
from .specs.ground_truth import ground_truth_builders


def is_correct(kind : str, task_name : str, answer : str) -> bool :
    if not answer.strip() :
        return False

    alphabet = tasks_alphabets[task_name]

    if kind == "regex" :
        nfa = regex_to_nfa(answer, alphabet)

        if isinstance(nfa, str) :
            return False

    elif kind == "automata" :
        parsed = parse_answer(answer)

        if isinstance(parsed, str) :
            return False

        if parsed.alphabet - set(alphabet) :
            return False

        nfa = NFA(parsed.start_states, alphabet, parsed.finish_states)

    else :
        raise ValueError(f"Неизвестный тип эксперимента: {kind}")

    dfa = nfa_to_dfa(nfa)
    ground_truth = ground_truth_builders[task_name]()

    return equivalent_dfa(dfa, ground_truth)


def checked_correct(
    kind : str,
    task_name : str,
    answer : str
) -> bool | None :
    try :
        return is_correct(kind, task_name, answer)
    except Exception as error :
        print(f"Не удалось проверить ответ: {error}", flush=True)
        return None


def load_statistics(folder : Path) -> dict :
    path = folder / "statistics.json"

    if not path.exists() :
        return {
            "version": 1,
            "attempts": {}
        }

    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("version") != 1 or not isinstance(data.get("attempts"), dict) :
        raise ValueError(f"Некорректный файл статистики: {path}")

    return data


def write_statistics(folder : Path, data : dict) -> None :
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / "statistics.json"
    temp_path = folder / "statistics.json.tmp"

    with temp_path.open("w", encoding="utf-8") as file :
        json.dump(data, file, ensure_ascii=False, indent=4)

    temp_path.replace(path)


def already_saved(path : Path, number : int) -> bool :
    data = load_statistics(path.parent)
    record = data["attempts"].get(str(number))

    if record is not None :
        if not path.exists() :
            path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("x", encoding="utf-8") as file :
                file.write(record["answer"])

        elif path.read_text(encoding="utf-8") != record["answer"] :
            raise ValueError(f"Ответ и статистика не совпадают: {path}")

        return True

    return path.exists()


def save_attempt(
    path : Path,
    number : int,
    kind : str,
    task_name : str,
    draft : str,
    answer : str,
    elapsed : float,
    cost : float,
    repair_attempted : bool
) -> None :
    data = load_statistics(path.parent)
    key = str(number)

    if path.exists() or key in data["attempts"] :
        raise FileExistsError(f"Попытка уже сохранена: {path}")

    data["attempts"][key] = {
        "draft": draft,
        "answer": answer,
        "draft_correct": checked_correct(kind, task_name, draft),
        "final_correct": checked_correct(kind, task_name, answer),
        "repair_attempted": repair_attempted,
        "elapsed": elapsed,
        "cost": cost
    }

    write_statistics(path.parent, data)

    with path.open("x", encoding="utf-8") as file :
        file.write(answer)


def print_statistics(folder : Path, recursive : bool = False) -> None :
    if recursive :
        stats_files = folder.rglob("statistics.json")
        answer_files = folder.rglob("*.txt")
    else :
        stats_files = folder.glob("statistics.json")
        answer_files = folder.glob("*.txt")

    records = []

    for path in sorted(stats_files) :
        data = load_statistics(path.parent)
        records.extend(data["attempts"].values())

    missing = 0

    for path in answer_files :
        suffix = path.stem.rsplit("__", 1)[-1]
        data = load_statistics(path.parent)

        if not suffix.isdigit() or str(int(suffix)) not in data["attempts"] :
            missing += 1

    def show_rate(label : str, field : str, items : list) -> None :
        checked = [
            item[field]
            for item in items
            if item[field] is not None
        ]

        correct = sum(value is True for value in checked)

        if checked :
            percent = f"{100 * correct / len(checked):.2f}%"
        else :
            percent = "—"

        print(f"{label}: {correct}/{len(checked)} ({percent})")

        if len(checked) < len(items) :
            print(f"Не удалось проверить: {len(items) - len(checked)}")

    title = "все задачи" if recursive else "текущая задача"
    print(f"\n=== Статистика: {title} ===")
    print(f"Попыток с метриками: {len(records)}")

    show_rate("Верные черновики", "draft_correct", records)
    show_rate("Верные итоговые ответы", "final_correct", records)

    repaired = [
        record for record in records
        if record["repair_attempted"]
    ]
    show_rate("Итог среди попыток с правкой", "final_correct", repaired)

    total_time = sum(record["elapsed"] for record in records)
    total_cost = sum(record["cost"] for record in records)

    print(f"Суммарное время: {total_time:.1f} с")
    print(f"Суммарная стоимость: ${total_cost:.6f}")

    if missing :
        print(f"Старых ответов без статистики: {missing}")