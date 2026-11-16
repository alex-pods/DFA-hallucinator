from openrouter import OpenRouter
import os
import requests
import json
from time import perf_counter

def openrouter_request(
        model: str,
        task: str,
        system_prompt : str
) -> tuple[str, float]:

    started = perf_counter()

    with OpenRouter(
            api_key=os.getenv("OPENROUTER_API_KEY", "")
    ) as open_router:
        res = open_router.chat.send(
            model=model,
            reasoning={"effort": "high"},
            # provider={
            #    "allow_fallbacks": False,
            #    "require_parameters": True,
            #    "data_collection": "deny",
            #    "max_price": {
            #        "prompt": "0.30",
            #        "completion": "1.20",
            #    },
            # },
            messages=[

                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": task
                }
            ]
        )

    choice = res.choices[0]
    usage = res.usage

    cost = 0.0
    if usage is not None:
        if isinstance(usage.cost, (int, float)):
            cost = float(usage.cost)
        print("Токены: вход " + str(usage.prompt_tokens) + ", выход " + str(usage.completion_tokens))

    print("Завершение:", choice.finish_reason)
    print(f"Стоимость: ${cost:.6f}")
    elapsed = perf_counter() - started

    return choice.message.content or "", cost, elapsed


def local_request(
    model : str,
    task : str,
    system_prompt : str,
    num_predict : int = -1,
    think : bool = True,
    details : dict | None = None
) -> tuple[str, float, float] :

    request_data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": task
            }
        ],
        "stream": True,
        "think": think,
        "options": {
            "num_ctx": 32768,
            "num_predict": num_predict,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0
        }
    }

    answer = ""
    thinking_parts = []
    phase = None
    finished = False
    started = perf_counter()

    print("Ждём генерацию Ollama...", flush=True)

    with requests.post(
        "http://localhost:11434/api/chat",
        json=request_data,
        stream=True,
        timeout=(10, 600)
    ) as response :

        response.raise_for_status()

        for line in response.iter_lines(chunk_size=1) :
            if not line :
                continue

            part = json.loads(line)

            if "error" in part :
                raise RuntimeError(part["error"])

            message = part.get("message", {})

            thinking = message.get("thinking") or ""
            content = message.get("content") or ""

            if thinking :
                if phase != "thinking" :
                    print("\nРассуждения:", flush=True)
                    phase = "thinking"

                if details is not None:
                    thinking_parts.append(thinking)

                print(thinking, end="", flush=True)

            if content :
                if phase != "answer" :
                    print("\nОтвет:", flush=True)
                    phase = "answer"

                print(content, end="", flush=True)
                answer += content

            if part.get("done") :
                finished = True

                if details is not None:
                    details["done_reason"] = part.get("done_reason")
                    details["thinking"] = "".join(thinking_parts)

                print(
                    "\nПричина завершения:",
                    part.get("done_reason"),
                    flush=True
                )
                print(
                    "Сгенерировано токенов:",
                    part.get("eval_count"),
                    flush=True
                )

                break

    if not finished :
        raise RuntimeError(
            "Поток Ollama оборвался до завершения ответа"
        )

    elapsed = perf_counter() - started
    print(f"Время запроса: {elapsed:.1f} с", flush=True)

    return answer, 0.0, elapsed

def request_for(source: str):
    if source == "local":
        return local_request
    if source == "openrouter":
        return openrouter_request

    raise ValueError(f"Неизвестный источник модели: {source}")



def local_request_two_stage(
    model : str,
    task : str,
    system_prompt : str
) -> tuple[str, float] :

    plan_prompt = """
Ты решаешь задачу построения регулярного выражения.

Дай краткий план решения, не более 100 слов:
1. Какие ограничения должны выполняться одновременно.
2. Какую структуру имеют допустимые слова.
3. Как выразить эту структуру через конкатенацию,
   альтернативу и звезду Клини.

Не переписывай условие.
Не перечисляй правила оформления.
"""

    print("\nЭтап 1: план решения", flush=True)

    plan, first_cost = local_request(
        model,
        task,
        plan_prompt
    )

    final_task = (
        task
        + "\n\nПредварительный план:\n"
        + plan
        + "\n\nПлан может содержать ошибки. "
        "Проверь его по исходному условию. "
        "Верни только итоговое регулярное выражение."
    )

    print("\nЭтап 2: регулярное выражение", flush=True)

    answer, second_cost = local_request(
        model,
        final_task,
        system_prompt
    )

    return answer, first_cost + second_cost


