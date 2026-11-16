import argparse

from lab.experiments.experiment_strategy import AutomataExperiment, Experiment, RegexExperiment

EXPERIMENTS: dict[str, Experiment] = {
    "automata": AutomataExperiment(),
    "regex": RegexExperiment()
}

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("experiment", choices=EXPERIMENTS)
    parser.add_argument("model", help="Имя модели в Ollama или ID в openrouter")
    parser.add_argument(
        "--iterations",
        type=int,
        required=True,
        help="Сколько ответов должно быть на каждую задачу"
    )
    parser.add_argument("--source", choices=("local", "openrouter"))

    parser.add_argument(
        "--pipeline",
        choices=("single", "repair", "parallel_tests"),
        default="single",
    )

    parser.add_argument(
        "--draft-limit",
        type=int,
        default=-1,
    )

    parser.add_argument(
        "--repair-limit",
        type=int,
        default=-1,
    )

    parser.add_argument(
        "--test-limit",
        type=int,
        default=-1,
    )
    args = parser.parse_args()

    if args.iterations < 1:
        parser.error("--iterations должно быть положительным числом")
    experiment = EXPERIMENTS[args.experiment]
    source = args.source or experiment.default_source

    if source not in experiment.supported_sources:
        parser.error(f"Эксперимент {args.experiment} не поддерживает источник {source}")

    if (
            args.pipeline in ("repair", "parallel_tests")
            and source != "local"
    ):
        parser.error(
            f"--pipeline {args.pipeline} пока поддерживает "
            "только --source local"
        )

    for limit in (
            args.draft_limit,
            args.repair_limit,
            args.test_limit,
    ):
        if limit != -1 and limit < 1:
            parser.error(
                "Лимит должен быть положительным числом или -1"
            )

    experiment.run(
        args.model,
        args.iterations,
        source,
        pipeline=args.pipeline,
        draft_limit=args.draft_limit,
        repair_limit=args.repair_limit,
        test_limit=args.test_limit,
    )

if __name__ == "__main__":
    main()