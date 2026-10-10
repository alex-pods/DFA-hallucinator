from misc import *
from openrouter_requester import *
from fileIO import *
from automata import *


RUN_NAME = "run_001"

tasks = {
    "basic": """число ноликов чётно, число единиц нечётно, нет подстрок 00 и нет подстрок 11,
                алфавит {0 , 1}""",

    "4th-symbol": "четвёртый символ с конца равен 1, алфавит {0 , 1}",

    "employer": """ID сотрудника: начинается с 3 букв региона,
                потом 4 цифры, причем если регион SPB,
                то цифры не могут начинаться с нуля,
                алфавит для простоты возьмем такой: {A, M, C, S, P, B, 0, 1, 2, 3, 4, 5}""",

    "intersection": r"""L = (A)^R \cap B,
                    где A = \{w \in \{0,1\}^*, третий символ с начала равен 1\},
                    B = \{w \in \{0,1\}^*, w содержит ровно один 0\}""",

    "abc-bca-cab": "слово состоит только из конкатенированных циклических сдвигов abc {a, b, c}",
}
tasks_tests = {
    "basic": {
        "": "deny",
        "0": "deny",
        "1": "accept",
        "01": "deny",
        "10": "deny",
        "010": "accept",
        "101": "deny",
        "001": "deny",
        "111": "deny",
        "10101": "accept",
        "01010": "deny",
        "11010": "deny",
        "0101010": "accept",
        "101010101": "accept",
        "01010101010": "accept",
    },

    "4th-symbol": {
        "": "deny",
        "1": "deny",
        "11": "deny",
        "101": "deny",
        "0000": "deny",
        "1000": "accept",
        "1010": "accept",
        "1111": "accept",
        "0111": "deny",
        "01000": "accept",
        "10000": "deny",
        "001000": "accept",
        "110111": "deny",
        "1010101": "deny",
        "0001000": "accept",
    },

    "employer": {
        "": "deny",
        "SPB1234": "accept",
        "SPB5000": "accept",
        "SPB0123": "deny",
        "SPB0000": "deny",
        "AMC0000": "accept",
        "AAA0123": "accept",
        "SPA0000": "accept",
        "SBP0000": "accept",
        "SPB123": "deny",
        "SPB12345": "deny",
        "SP1234": "deny",
        "SPBA1234": "deny",
        "1PB1234": "deny",
        "SPB12A4": "deny",
    },

    "intersection": {
        "": "deny",
        "0": "deny",
        "01": "deny",
        "111": "deny",
        "011": "deny",
        "101": "accept",
        "110": "accept",
        "0111": "accept",
        "1011": "deny",
        "1101": "accept",
        "1110": "accept",
        "1100": "deny",
        "11011": "deny",
        "11101": "accept",
        "011111": "accept",
    },

    "abc-bca-cab": {
        "": "accept",
        "abc": "accept",
        "bca": "accept",
        "cab": "accept",
        "abcabc": "accept",
        "abcbca": "accept",
        "bcacab": "accept",
        "cabbcaabc": "accept",
        "a": "deny",
        "ab": "deny",
        "acb": "deny",
        "abcab": "deny",
        "abccba": "deny",
        "ababcc": "deny",
        "abcabcab": "deny",
    },
}

def parse_qwen_answer(answer: str) :
    return answer.split("</think>")[-1].strip()

def get_answers(model : str, iterations : int, task_name : str) -> float :
    ttl_cost = 0.0
    for i in range(0, iterations) :
        path = answer_path(RUN_NAME, model, task_name, i)
        if path.exists():
            continue

        answer, cost = openrouter_request(model, tasks[task_name])
        answer = parse_qwen_answer(answer)
        ttl_cost += cost

        save_answer(RUN_NAME, model, task_name, i, answer)
        print(task_name + ": сохранён ответ "+str(i+1)+"/" + str(iterations))
        print(f"Потрачено на задачу: ${ttl_cost:.6f}\n")
    return ttl_cost

# if __name__ == "__main__":
#      total_cost = 0.0
#      for task_name in tasks.keys() :
#          total_cost += get_answers("qwen/qwen3.5-flash-02-23", 50, task_name)
#      print(f"Всего потрачено: ${total_cost:.6f}")


def check_results(model_folder_name : str) :
    root = Path("experiments") / RUN_NAME / model_folder_name

    for task in tasks.keys() :
        format_error_counts = {}
        root_task = root / task

        dfa_counter = 0
        nfa_counter = 0
        sum_out_states = 0
        sum_finish_states_dfa = 0
        sum_finish_states_nfa = 0
        sum_start_states_nfa = 0
        sum_all_states_dfa = 0
        sum_all_states_nfa = 0

        false_accept_count = 0
        false_deny_count = 0
        true_accept_count = 0
        true_deny_count = 0

        sum_dfa_states_global = 0

        correct_automata = 0

        for path in sorted(root_task.rglob("*.txt")):
            number = int(path.stem.rsplit("__", 1)[1])


            answer = path.read_text(encoding="utf-8")
            parsed = parse_answer(answer)

            if isinstance(parsed, str) :
                format_error_counts[parsed] = format_error_counts.get(parsed, 0) + 1
                #print(f"Ошибка формата в автомате номер {number}: " + parsed + '\n' + answer)
                continue

            if len(parsed.start_states) == 1 and all(len(set(targets)) <= 1 for st in parsed.states for targets in st.transitions.values()) :
                dfa_counter += 1
                sum_finish_states_dfa += len(parsed.finish_states)
                sum_all_states_dfa += len(parsed.states)
            else :
                nfa_counter += 1
                sum_out_states  += sum(sum(len(set(targets)) for targets in st.transitions.values()) for st in parsed.states) / len(parsed.states)
                sum_finish_states_nfa += len(parsed.finish_states)
                sum_start_states_nfa += len(parsed.start_states)
                sum_all_states_nfa += len(parsed.states)

            nfa = NFA(parsed.start_states, parsed.alphabet, parsed.finish_states)
            tests = tasks_tests[task]
            passed_count = 0

            for word, exp in tests.items() :
                res = nfa.compute(word)

                if res == exp:
                    passed_count += 1
                if res == exp and exp == "accept" :
                    true_accept_count += 1
                if res == exp and exp == "deny" :
                    true_deny_count += 1
                if res != exp and exp == "accept" :
                    false_deny_count += 1
                if res != exp and exp == "deny" :
                    false_accept_count += 1

            if tests and passed_count == len(tests):
                correct_automata += 1

            dfa = nfa_to_dfa(nfa)

            sum_dfa_states_global += dfa.total_states

        def average(total, count):
            return f"{total / count:.2f}" if count else "—"

        def percent(part, total):
            return f"{100 * part / total:.2f}%" if total else "—"

        valid_count = dfa_counter + nfa_counter
        format_error_count = sum(format_error_counts.values())
        total_count = valid_count + format_error_count
        print("======================================================")
        print(f"Модель: {model_folder_name} Задача: {task}")
        print("======================================================\n")

        print(f"\n=== Ответы\nВсего ответов: {total_count}")
        print(f"Корректный формат: {valid_count}")
        print(f"Ошибки формата: {format_error_count}")
        for error, count in sorted(format_error_counts.items()):
            print(f"{error}: {count}")

        print(f"\n=== Автоматы\n")
        print(f"DFA: {dfa_counter}")
        print(f"Процент DFA: {percent(dfa_counter, valid_count)}")
        print(f"NFA: {nfa_counter}")
        print(f"Процент NFA: {percent(nfa_counter, valid_count)}")

        print(f"\n=== Средние характеристики автоматов\n")
        print(f"Состояний в DFA: {average(sum_all_states_dfa, dfa_counter)}")
        print(f"Принимающих состояний в DFA: {average(sum_finish_states_dfa, dfa_counter)}")

        print(f"Состояний в NFA: {average(sum_all_states_nfa, nfa_counter)}")
        print(f"Принимающих состояний в NFA: {average(sum_finish_states_nfa, nfa_counter)}")
        print(f"Начальных состояний в NFA: {average(sum_start_states_nfa, nfa_counter)}")
        print(f"Исходящих переходов в NFA: {average(sum_out_states, nfa_counter)}")

        print(f"\n=== После детерменизации\n")
        print(f"Состояний в DFA: {average(sum_dfa_states_global, valid_count)}")

        tests_total = (true_accept_count + true_deny_count) + (false_accept_count + false_deny_count)

        print(f"\n=== Результаты запуска автоматов\n")
        print(f"Процент правдивых ответов: {percent(true_accept_count + true_deny_count, tests_total)}")
        print(f"Процент правдивых принятий(относительно всех принятий): {percent(true_accept_count, true_accept_count + false_accept_count)}")
        print(f"Процент правдивых отвержений(относительно всех отвержений): {percent(true_deny_count, true_deny_count + false_deny_count)}")

        print(f"\n=== Итог\n")
        print(f"Прошли все тесты: {correct_automata}")
        print(f"Среди всех ответов LLM: {percent(correct_automata, total_count)}")


#check_results("openai__gpt-6-luna")
#check_results("deepseek__deepseek-v4.1-flash")
#check_results("xiaomi__mimo-v2.6-pro")
#check_results("z-ai__glm-5.3")

check_results("qwen__qwen3.5-flash-02-23")

# gpt 6 luna ~$0.018000 basic
# gpt 6 luna ~$0.018000 4th-symbol
# gpt 6 luna ~$0.018000 employer
# gpt 6 luna  $0.023756 intersection
# gpt 6 luna  $0.008738 abc-bca-cab
# gpt 6 luna  $0,089000 total

# deepseek 4.1 flash $0.049613 basic
# deepseek 4.1 flash $0.027777 4th-symbol
# deepseek 4.1 flash $0.058395 employer
# deepseek 4.1 flash $0.056259 intersection
# deepseek 4.1 flash $0.035873 abc-bca-cab
# deepseek 4.1 flash $0.178305 total

# xiaomi mimo v2.6 pro $0.095734 basic
# xiaomi mimo v2.6 pro $0.082924 4th-symbol
# xiaomi mimo v2.6 pro $0.077908 employer
# xiaomi mimo v2.6 pro $0.157236 intersection
# xiaomi mimo v2.6 pro $0.057421 abc-bca-cab
# xiaomi mimo v2.6 pro $0,471223 total

# z-ai glm v5.3 $0.132319 basic
# z-ai glm v5.3 $0.083759 4th-symbol
# z-ai glm v5.3 $0.272199 employer
# z-ai glm v5.3 $0.321347 intersection
# z-ai glm v5.3 $0.082086 abc-bca-cab
# z-ai glm v5.3 $0.891709 total 😥 в 10 раз дороже гпт

# qwen qwen3.5 flash $0.113352 basic
# qwen qwen3.5 flash $0.083348 4th-symbol
# qwen qwen3.5 flash $0.106335 employer
# qwen qwen3.5 flash $0.166875 intersection
# qwen qwen3.5 flash $0.184193 abc-bca-cab
# qwen qwen3.5 flash $0.654103 total