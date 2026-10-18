from pathlib import Path
from automata import DFA

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


def save_dfa(dfa : DFA, path : Path) :
    path.parent.mkdir(parents=True, exist_ok=True)

    state_ids = {}
    for i, st in enumerate(dfa.states) :
        state_ids[st] = i

    with path.open("w", encoding="utf-8") as file :
        file.write(str(len(dfa.states)) + "\n")
        file.write(str(len(dfa.alphabet)) + "\n")
        file.write(str(state_ids[dfa.start_state]) + "\n")

        finish_ids = []
        for st in dfa.finish_states :
            finish_ids.append(str(state_ids[st]))

        file.write(" ".join(finish_ids) + "\n")

        for st in dfa.states :
            for letter in sorted(dfa.alphabet) :
                next_state = st.next(letter)

                file.write(
                    str(state_ids[st]) + " "
                    + letter + " "
                    + str(state_ids[next_state]) + "\n"
                )