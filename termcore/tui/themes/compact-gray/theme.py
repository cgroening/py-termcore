from textual.theme import Theme

TEXTUAL_THEME = Theme(
    name="compact-gray",
    primary="#8BD3CD",
    secondary="#646464",
    accent="#A9B7C6",
    foreground="#E5E5E5",
    background="#151515",
    surface="#3E3E3E",
    panel="#101010",
    boost="#444C5E",
    success="#A3C995",
    warning="#dfd483",
    error="#D67B76",
    dark=True,
    variables={
        "block-hover-background": "#335D48",
        "footer-key-foreground": "#D2D05F",
        "input-cursor-text-style": "reverse",
    }
)
