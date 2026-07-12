from textual.theme import Theme


TEXTUAL_THEME = Theme(
    name="classic-black-saturated",
    primary="#5C9AC3",
    secondary="#5B5B5B",
    accent="#A9B7C6",
    foreground="#E5E5E5",
    background="#0D0E10",
    surface="#1E2022",
    panel="#101112",
    boost="#016F60",
    success="#84D667",
    warning="#E6B863",
    error="#DA5E57",
    dark=True,
    variables={
        "block-hover-background": "#0c4d5e",
        "footer-key-foreground": "#D2D05F",
        "input-cursor-text-style": "reverse",
    }
)