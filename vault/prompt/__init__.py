def mfa_prompt(message, use_ui_prompt=False):
    if not use_ui_prompt:
        return input(message)
    from vault.prompt.qt.prompt import MFAUiPrompt
    return MFAUiPrompt().prompt(title=message)
