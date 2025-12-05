"""
Small helper module that declares function-callable tools for the GenAI SDK.

This file keeps all function-declaration and implementation details out of
`ai.py` so only a tiny import and a single `config=` change are required
in the main generation loop. The functions here are intentionally simple and mockable.
"""

import datetime

from google.genai import types


def get_time() -> str:
    """Return the current time for a given location.

    Returns:
        A human-readable string with the current time for the location.
    """
    print("\033[94mGetting time\033[0m")

    now = datetime.datetime.now()
    readable = now.strftime("%Y-%m-%d %H:%M:%S")

    return f"Current time UTC: {readable}"


def get_generate_config(disable_automatic: bool = False) -> types.GenerateContentConfig:
    """Return a GenAI GenerateContentConfig with our function tools attached.

    By passing Python callables directly, the Google GenAI Python SDK will
    automatically create function declarations from the callables' type hints
    and docstrings and (when enabled) execute them when the model requests
    a function call. This keeps integration minimal in `ai.py`.

    Args:
        disable_automatic: If True, disable automatic function calling (SDK will
                           return function_call suggestions instead of executing).

    Returns:
        A `types.GenerateContentConfig` instance configured with our tools.
    """

    # Pass the callables directly so the SDK can infer schemas and handle calls.
    tools = [get_time]

    config = types.GenerateContentConfig(tools=tools)
    if disable_automatic:
        config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
            disable=True
        )

    return config
