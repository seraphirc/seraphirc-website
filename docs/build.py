#!/usr/bin/env python3
"""Regenerate the command reference inside docs/index.html from commands.json.

commands.json is a straight dump of `commands.Registry` from the client repo
(seraphirc-core/commands/commands.go), which is the same table that answers
/help inside the app. That keeps the site and the client from drifting: the
prose around the commands is hand written, the command entries are not.

To refresh the data, drop a throwaway program into the client repo:

    // ~/projects/seraphirc/seraphirc-core/cmd/dumpcmds/main.go
    package main

    import (
        "encoding/json"
        "os"

        "github.com/seraphirc/seraphirc-source/seraphirc-core/commands"
    )

    func main() {
        enc := json.NewEncoder(os.Stdout)
        enc.SetIndent("", "  ")
        if err := enc.Encode(commands.Registry); err != nil {
            panic(err)
        }
    }

then:

    cd ~/projects/seraphirc/seraphirc-core
    go run ./cmd/dumpcmds > ~/projects/seraphirc-website/docs/commands.json
    rm -rf cmd/dumpcmds

    cd ~/projects/seraphirc-website
    python3 docs/build.py

Only the regions between the BEGIN:/END: marker comments in docs/index.html
are rewritten. Everything else in that file is hand written and left alone.
"""

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "commands.json"
PAGE = HERE / "index.html"

# Same order the client uses for its /help overview.
CATEGORY_ORDER = [
    "Connection",
    "Messaging",
    "Encryption",
    "IRC",
    "IRC Operator",
    "Services",
    "Buffers",
    "Client",
    "Advanced",
]

# One hand written sentence per category, shown under the category title.
CATEGORY_LEADS = {
    "Connection": "Bringing a network up and down, and getting in and out of "
    "channels. Most need an active network. See "
    "<a href=\"#connecting\">Connecting to a Network</a>.",
    "Messaging": "Putting text, files, or an action in front of someone. The "
    "formatting variants are covered under "
    "<a href=\"#formatting\">Text Formatting</a>.",
    "Encryption": "FiSH message encryption, compatible with HexChat, "
    "Konversation, Quassel, and mIRC FiSH 10. Set a shared key and messages "
    "to that buffer encrypt automatically. See "
    "<a href=\"#encryption\">Encrypted Messaging</a>.",
    "IRC": "Standard IRC verbs, passed to the server. Operator commands such "
    "as <code>/op</code> and <code>/kick</code> only work when you hold status "
    "in the channel.",
    "IRC Operator": "Server administration. These need an operator block, and "
    "most are non standard, so what works depends on your network's ircd.",
    "Services": "Shortcuts to the service bots. Each sends to the service "
    "target configured for that network, so a mistyped target cannot drop your "
    "password into a channel.",
    "Buffers": "Buffers are your windows: server, channel, and query. These "
    "move between them, tidy them, and close them. None touch the network.",
    "Client": "SeraphIRC itself rather than IRC. Help, aliases, the ignore "
    "list, notify entries, and the About panel.",
    "Advanced": "The escape hatch. If SeraphIRC has no command for something "
    "your network supports, send the line yourself.",
}

FLAG_LABELS = [
    ("SendsIRC", "sends IRC", "flag-irc"),
    ("LocalOnly", "local only", "flag-local"),
    ("RequiresNetwork", "needs a network", "flag-network"),
    ("RequiresBuffer", "needs a buffer", "flag-buffer"),
]


def esc(text):
    return html.escape(str(text), quote=False)


def category_slug(name):
    return "commands-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def command_slug(name):
    return "cmd-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_commands():
    registry = json.loads(DATA.read_text(encoding="utf-8"))
    unknown = {c["Category"] for c in registry} - set(CATEGORY_ORDER)
    if unknown:
        raise SystemExit(
            "commands.json has categories build.py does not know about: "
            + ", ".join(sorted(unknown))
            + "\nAdd them to CATEGORY_ORDER and CATEGORY_LEADS."
        )
    grouped = {name: [] for name in CATEGORY_ORDER}
    for command in registry:
        grouped[command["Category"]].append(command)
    for commands in grouped.values():
        commands.sort(key=lambda c: c["Name"])
    return registry, grouped


def render_flags(command):
    flags = [
        f'<span class="flag {css}">{label}</span>'
        for key, label, css in FLAG_LABELS
        if command.get(key)
    ]
    if not flags:
        return ""
    return '<span class="entry-flags">' + "".join(flags) + "</span>"


def render_parameters(command):
    parameters = command.get("Parameters") or []
    if not parameters:
        return ""
    rows = []
    for parameter in parameters:
        name, _, description = parameter.partition(": ")
        if not description:
            rows.append(f"<dt>{esc(name)}</dt><dd></dd>")
        else:
            rows.append(
                f"<dt><code>{esc(name)}</code></dt><dd>{esc(description)}</dd>"
            )
    return (
        '            <h4 class="entry-label">Parameters</h4>\n'
        '            <dl class="entry-params">'
        + "".join(rows)
        + "</dl>\n"
    )


def render_details(command):
    details = command.get("Details") or []
    if not details:
        return ""
    body = "".join(f"<p>{esc(line)}</p>" for line in details)
    return f'            <div class="entry-details">{body}</div>\n'


def render_examples(command):
    examples = command.get("Examples") or []
    if not examples:
        return ""
    lines = "\n".join(esc(example) for example in examples)
    return (
        '            <h4 class="entry-label">Examples</h4>\n'
        f'            <pre class="entry-examples"><code>{lines}</code></pre>\n'
    )


def render_aliases(command):
    aliases = command.get("Aliases") or []
    if not aliases:
        return ""
    listed = ", ".join(f"<code>/{esc(alias)}</code>" for alias in sorted(aliases))
    return f'            <p class="entry-aliases">Also written as {listed}</p>\n'


def render_entry(command):
    name = esc(command["Name"])
    slug = command_slug(command["Name"])
    parts = [
        f'          <section class="docs-entry" id="{slug}">\n',
        '            <header class="entry-head">\n',
        f'              <h3>/{name}<a class="entry-anchor" href="#{slug}"'
        f' aria-label="Link to /{name}">#</a></h3>\n',
    ]
    flags = render_flags(command)
    if flags:
        parts.append(f"              {flags}\n")
    parts.append("            </header>\n")
    parts.append(
        f'            <p class="entry-usage"><code>{esc(command["Usage"])}</code></p>\n'
    )
    if command.get("Summary"):
        parts.append(
            f'            <p class="entry-summary">{esc(command["Summary"])}</p>\n'
        )
    parts.append(render_aliases(command))
    parts.append(render_parameters(command))
    parts.append(render_details(command))
    parts.append(render_examples(command))
    parts.append("          </section>\n")
    return "".join(parts)


def render_category_pane(category, commands):
    slug = category_slug(category)
    jump = "".join(
        f'<a href="#{command_slug(c["Name"])}"><code>/{esc(c["Name"])}</code></a>'
        for c in commands
    )
    out = [
        f'        <article class="docs-pane" id="{slug}" data-pane>\n',
        '          <p class="pane-kicker">Commands</p>\n',
        f"          <h2>{esc(category)}</h2>\n",
        f'          <p class="pane-lead">{CATEGORY_LEADS[category]}</p>\n',
        f'          <nav class="entry-jump" aria-label="{esc(category)} commands">{jump}</nav>\n',
    ]
    out.extend(render_entry(command) for command in commands)
    out.append("        </article>\n")
    return "".join(out)


def render_index_pane(registry):
    rows = []
    for command in sorted(registry, key=lambda c: c["Name"]):
        slug = command_slug(command["Name"])
        aliases = command.get("Aliases") or []
        alias_text = (
            ", ".join(f"/{esc(a)}" for a in sorted(aliases)) if aliases else ""
        )
        rows.append(
            "              <tr>"
            f'<th scope="row"><a href="#{slug}"><code>/{esc(command["Name"])}</code></a></th>'
            f'<td class="idx-alias"><code>{alias_text}</code></td>'
            f'<td>{esc(command["Summary"])}</td>'
            f'<td class="idx-cat"><a href="#{category_slug(command["Category"])}">'
            f'{esc(command["Category"])}</a></td>'
            "</tr>\n"
        )
    return (
        '        <article class="docs-pane" id="command-index" data-pane>\n'
        '          <p class="pane-kicker">Commands</p>\n'
        "          <h2>Command Index</h2>\n"
        f'          <p class="pane-lead">Every command SeraphIRC answers, all '
        f'{len(registry)} of them, in one alphabetical list. The client keeps '
        "the same list behind <code>/help</code>.</p>\n"
        '          <div class="table-scroll">\n'
        '            <table class="idx-table">\n'
        "              <thead><tr><th>Command</th><th>Also</th><th>Summary</th>"
        "<th>Section</th></tr></thead>\n"
        "              <tbody>\n" + "".join(rows) + "              </tbody>\n"
        "            </table>\n"
        "          </div>\n"
        "        </article>\n"
    )


def render_nav(grouped):
    out = []
    for category in CATEGORY_ORDER:
        commands = grouped[category]
        slug = category_slug(category)
        items = "".join(
            f'              <li><a href="#{command_slug(c["Name"])}">'
            f'<code>/{esc(c["Name"])}</code></a></li>\n'
            for c in commands
        )
        out.append(
            f'          <details class="chapter">\n'
            f"            <summary>{esc(category)}"
            f'<span class="chapter-count">{len(commands)}</span></summary>\n'
            f'            <ul class="pagelist">\n'
            f'              <li class="page-overview"><a href="#{slug}">'
            f'<span class="lbl-screen">All {esc(category.lower())} commands</span>'
            f'<span class="lbl-print">{esc(category)}</span></a></li>\n'
            f"{items}"
            f"            </ul>\n"
            f"          </details>\n"
        )
    return "".join(out)


def replace_region(page, marker, body):
    pattern = re.compile(
        r"(<!-- BEGIN:%s -->\n).*?(\s*<!-- END:%s -->)" % (marker, marker),
        re.DOTALL,
    )
    if not pattern.search(page):
        raise SystemExit(f"docs/index.html has no BEGIN:{marker} region")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2).lstrip("\n"), page)


def main():
    registry, grouped = load_commands()
    page = PAGE.read_text(encoding="utf-8")

    panes = "".join(
        render_category_pane(category, grouped[category])
        for category in CATEGORY_ORDER
    )
    panes += render_index_pane(registry)

    page = replace_region(page, "nav-commands", render_nav(grouped))
    page = replace_region(page, "panes-commands", panes)

    PAGE.write_text(page, encoding="utf-8")
    print(
        f"docs/index.html: {len(registry)} commands across "
        f"{len(CATEGORY_ORDER)} sections",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
