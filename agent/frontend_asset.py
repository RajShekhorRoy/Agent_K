STICKY_HEADER =    """
<style>
    div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
        position: sticky;
        top: 2.875rem;
        color: #02665D;
        background-color: #FDFDF8;
        z-index: 999;
        overflow: hidden;
        max-width: 100vw;
        box-sizing: border-box;
    }
    .fixed-header {
        border-bottom: 1px solid black;
    }
</style>
    """

button_style ="""
<style>

button[kind="secondary"] {
    background-color: #e53935;
    color: white;
    border-radius: 6px;
}
button[kind="secondary"]:hover {
    background-color: #c62828;
}

button[kind="primary"] {
    background-color: #188d62;
    color: white;
    border-radius: 6px;
    border-color:#26db99;
}
button[kind="primary"]:hover {
    background-color: #05b571;
}
</style>
"""


