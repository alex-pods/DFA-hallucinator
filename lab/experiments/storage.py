import json
from pathlib import Path

from lab.automata import DFA


REGEX_ROOT = Path("regex_experiments")


def _model_folder(model : str) -> str :
    return model.replace("/", "__").replace("\\", "__").replace(":", "__")


def _run_dir(root : Path, run : str, source : str) -> Path :
    if source not in ("local", "openrouter") :
        raise ValueError(f"Неизвестный источник модели: {source}")

    return root / run / source


def automata_run_dir(
    run : str,
    source : str = "openrouter",
    *,
    minimized : bool = False
) -> Path :
    root = Path("minimized" if minimized else "experiments")
    return _run_dir(root, run, source)


def answer_path(
    run : str,
    model : str,
    task : str,
    number : int,
    source : str = "openrouter"
) -> Path :
    model_folder = _model_folder(model)
    folder = automata_run_dir(run, source) / model_folder / task
    filename = f"{model_folder}__{task}__{number:03d}.txt"

    return folder / filename


def regex_answer_path(
    run : str,
    source : str,
    model : str,
    task : str,
    number : int
) -> Path :
    folder = _run_dir(REGEX_ROOT, run, source) / _model_folder(model) / task
    filename = f"{task}__{number:03d}.txt"

    return folder / filename


def _write_new_answer(path : Path, answer : str) -> None :
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("x", encoding="utf-8") as file :
        file.write(answer)


def save_answer(
    run : str,
    model : str,
    task : str,
    number : int,
    answer : str,
    source : str = "openrouter"
) -> None :
    path = answer_path(run, model, task, number, source)
    _write_new_answer(path, answer)


def save_regex_answer(
    run : str,
    source : str,
    model : str,
    task : str,
    number : int,
    answer : str
) -> None :
    path = regex_answer_path(run, source, model, task, number)
    _write_new_answer(path, answer)


def save_settings(path : Path, settings : dict) -> None :
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() :
        old_settings = json.loads(path.read_text(encoding="utf-8"))

        if old_settings != settings :
            raise ValueError(
                "Условия эксперимента поменялись. Нужно изменить RUN_NAME."
            )

        return

    with path.open("x", encoding="utf-8") as file :
        json.dump(settings, file, ensure_ascii=False, indent=4)


def save_dfa(dfa : DFA, path : Path) -> None :
    path.parent.mkdir(parents=True, exist_ok=True)

    state_ids = {}
    for i, state in enumerate(dfa.states) :
        state_ids[state] = i

    with path.open("w", encoding="utf-8") as file :
        file.write(f"{len(dfa.states)}\n")
        file.write(f"{len(dfa.alphabet)}\n")
        file.write(f"{state_ids[dfa.start_state]}\n")

        finish_ids = []
        for state in dfa.finish_states :
            finish_ids.append(str(state_ids[state]))

        file.write(" ".join(finish_ids) + "\n")

        for state in dfa.states :
            for letter in sorted(dfa.alphabet) :
                next_state = state.next(letter)
                file.write(
                    f"{state_ids[state]} {letter} {state_ids[next_state]}\n"
                )

def save_pipeline_artifacts(
    answer_path: Path,
    data: dict,
) -> Path:
    result_path = answer_path.with_name(
        f"{answer_path.stem}__pipeline.json"
    )

    temp_path = result_path.with_suffix(".json.tmp")

    result_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",   
    )

    temp_path.replace(result_path)

    return result_path