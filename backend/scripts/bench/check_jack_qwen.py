"""Compile the saved Qwen code, run cases and check with supplied checker rules."""
import json
import pathlib
import subprocess
import sys


def check(a0, output, strict=True):
    steps = [line.strip() for line in output.splitlines()]
    if len(steps) != 3:
        return False
    current = a0
    for step in steps:
        if not step or step[0] == '+' or step[-1] == '+' or '++' in step:
            return False
        parts = step.split('+')
        if ''.join(parts) != current:
            return False
        if strict and any(len(p) > 1 and p[0] == '0' for p in parts):
            return False
        try:
            current = str(sum(int(p) for p in parts))
        except ValueError:
            return False
    return len(current) == 1


def digit_sum(n):
    return sum(map(int, str(n)))


def candidates(n):
    s = str(n)
    out = ['+'.join(s)]
    if len(s) >= 2:
        out += ['+'.join([s[:2], *s[2:]]), '+'.join([*s[:-2], s[-2:]])]
    return out + [s]


def main():
    root = pathlib.Path(sys.argv[1])
    raw = json.loads((root / 'jack_response.json').read_text(encoding='utf-8'))
    content = raw['response']['message']['content']
    code = content.split('```cpp\n', 1)[1].split('```', 1)[0]
    source = root / 'jack_qwen.cpp'
    source.write_text(code, encoding='utf-8')
    binary = root / ('jack_qwen.exe' if sys.platform == 'win32' else 'jack_qwen')
    build = subprocess.run(['g++', '-std=c++17', '-O2', str(source), '-o', str(binary)], capture_output=True, text=True)
    if build.returncode:
        raise RuntimeError(build.stderr)
    # Exhaustively inspect the exact four-candidate rule over all reachable first sums.
    first_failure = None
    for n in range(1, 1800001):
        valid = [expr for expr in candidates(n) if digit_sum(sum(map(int, expr.split('+')))) <= 9]
        if not valid:
            first_failure = n
            break
    cases = ['1', '5806', '199', '289', '99999999999991999999999', '9' * 200000]
    if first_failure:
        q, r = divmod(first_failure, 9)
        cases.append('9' * q + (str(r) if r else ''))
    results = []
    for i, a0 in enumerate(cases):
        inp = f'{len(a0)}\n{a0}\n'
        run = subprocess.run([str(binary.resolve())], input=inp, capture_output=True, text=True, timeout=10)
        (root / f'jack_case_{i}.in').write_text(inp)
        (root / f'jack_case_{i}.out').write_text(run.stdout)
        results.append({'case': i, 'n': len(a0), 'a0_preview': a0[:100], 'exit': run.returncode,
                        'checker_pass': check(a0, run.stdout), 'statement_pass': check(a0, run.stdout, False),
                        'last_two_lines': run.stdout.splitlines()[-2:]})
    report = {'first_candidate_rule_failure_sum': first_failure, 'cases': results}
    (root / 'jack_validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
