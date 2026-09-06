from __future__ import annotations


def evaluate_exact_tokens(output: str, tokens: list[str]) -> list[dict[str, object]]:
    if not isinstance(output, str):
        raise ValueError("output must be a string")
    if not isinstance(tokens, list) or any(not isinstance(token, str) or not token for token in tokens):
        raise ValueError("tokens must be a list of non-empty strings")
    return [
        {
            "token": token,
            "present": token in output,
            "state": "PASS" if token in output else "FAIL",
        }
        for token in tokens
    ]
