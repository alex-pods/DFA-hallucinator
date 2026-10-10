from openrouter import OpenRouter
import os

def openrouter_request(model: str, task: str) -> tuple[str, float]:

    with OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY", "")
    ) as open_router:
        res = open_router.chat.send(
            model=model,
            reasoning={ "effort": "high" },
            #provider={
            #    "allow_fallbacks": False,
            #    "require_parameters": True,
            #    "data_collection": "deny",
            #    "max_price": {
            #        "prompt": "0.30",
            #        "completion": "1.20",
            #    },
            #},
            messages=[

                {
                    "role": "system",
                    "content": """Тебе будет описан язык. Тебе нужно написать конечный автомат (NFA или DFA) для его распознания.
                    Ответ пиши в следующем формате:
                    
                    n //число состояний
                    m // размер алфавита
                    0 2 3// номера начальных состояний через пробел
                    9 5 6// номера конечных состояний через пробел
                    2 2 4// переход по символу "2" из состояния 2 в состояние 4
                    ...
                    1 a 3// переход по символу "a" из состояния 1 в состояние 3
                    
                    Соблюдая следующие правила:
                    1. Состояния обозначаются неотрицательными числами от 0 до n-1
                    2. Не используй markdown
                    3. Не приводи комментарии и пояснения
                    4. Эпсилон переходы запрещены
                    5. В качестве символа перехода допустимы любые utf-8 символы. Необходимо,
                    чтобы они были в описанном в задании алфавите 
                    
                    Пример правильного оформления ответа:

                    3
                    2
                    0
                    1
                    0 0 1
                    0 0 2
                    0 1 2
                    1 0 2
                    2 1 2
                    2 0 0

                    Оставь только автомат. В виде, аналогичном тому что выше.
                    """
                },
                {
                    "content" : task,
                    "role" : "user"
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
    return str(choice.message.content) or "", cost

