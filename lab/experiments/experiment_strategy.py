from abc import ABC, abstractmethod

from .experiment_DFA_NFA import get_answers
from .experiment_regex import get_regex_answers
from .specs.tasks import tasks


class Experiment(ABC) :
    default_source : str
    supported_sources = ("local", "openrouter")

    @abstractmethod
    def collect_task(
        self,
        model : str,
        iterations : int,
        task_name : str,
        source : str,
        **pipeline_options
    ) -> tuple[float, float] :
        pass

    def run(
        self,
        model : str,
        iterations : int,
        source : str,
        **pipeline_options
    ) -> None :
        total_cost = 0.0
        total_time = 0.0

        for task_name in tasks :
            print(f"\nЗадача: {task_name}", flush=True)

            cost, elapsed = self.collect_task(
                model, iterations, task_name, source,
                **pipeline_options
            )

            total_cost += cost
            total_time += elapsed

        print(f"\nСтоимость новых запросов: ${total_cost:.6f}")
        print(f"Суммарное время новых попыток: {total_time:.1f} с")


class AutomataExperiment(Experiment) :
    default_source = "openrouter"

    def collect_task(
        self,
        model : str,
        iterations : int,
        task_name : str,
        source : str,
        **pipeline_options
    ) -> tuple[float, float] :
        return get_answers(
            model, iterations, task_name, source,
            **pipeline_options
        )


class RegexExperiment(Experiment) :
    default_source = "local"

    def collect_task(
        self,
        model : str,
        iterations : int,
        task_name : str,
        source : str,
        **pipeline_options
    ) -> tuple[float, float] :
        return get_regex_answers(
            model, iterations, task_name, source,
            **pipeline_options
        )