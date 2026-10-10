from pathlib import Path

def answer_path(run: str, model: str, task: str, number: int) -> Path:
    model = model.replace("/", "__").replace(":", "__")

    folder = Path("experiments") / run / model / task
    filename = model + "__" + task + "__" + f"{number:03d}" + ".txt"

    return folder / filename

def save_answer(run, model, task, number, answer) :
    path = answer_path(run, model, task, number)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("x", encoding="utf-8") as file :
        file.write(answer)