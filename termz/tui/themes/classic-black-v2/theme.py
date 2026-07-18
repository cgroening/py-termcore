from textual.theme import Theme

TEXTUAL_THEME = Theme(
    name="classic-black-v2",
    primary="#6D5498",
    secondary="#5B5B5B",
    accent="#A9B7C6",
    foreground="#E5E5E5",
    background="#101113",
    surface="#1E2022",
    panel="#242628",
    boost="#016F60",
    success="#A3C995",
    warning="#E6C384",
    error="#D67B76",
    dark=True,
    variables={
        "block-hover-background": "#4F3D6E",
        "cursor-line-background": "#6D80A6",
        "footer-key-foreground": "#D2D05F",
        "input-cursor-text-style": "reverse",
        "datatable-hover-background": "green",
    }
)
