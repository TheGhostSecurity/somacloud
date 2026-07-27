import json
import re
from pathlib import Path

from django.conf import settings
from django.utils.html import conditional_escape, escape, format_html, format_html_join
from django.utils.safestring import mark_safe


CONTENT_ROOT = settings.BASE_DIR / "content"


def relative_content_path(path):
    return str(path.relative_to(settings.BASE_DIR)).replace("\\", "/")


INLINE_RE = re.compile(r"(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|:tip\[([^\]]+)\]\{([^}]+)\}|:q\[([^\]]+)\]\{([^}]+)\})")


def _render_tip(visible, content):
    escaped = conditional_escape(content)
    return f'<span class="inline-tip cursor-pointer text-[#0067c0] underline decoration-dotted underline-offset-2" data-tip="{escaped}">{conditional_escape(visible)}<sup class="ml-0.5 text-[10px] font-bold">?</sup></span>'


def _render_question(question, options_raw):
    parts = [conditional_escape(p.strip()) for p in options_raw.split("|")]
    if len(parts) < 2:
        return conditional_escape(question)
    correct = parts[-1]
    choices = parts[:-1]
    qid = f"iq-{hash(question) & 0xFFFFFFFF}"
    html = f'<div class="inline-quiz my-4 rounded-lg border border-[#d0d0d0] bg-[#fafafa] p-4" data-correct="{conditional_escape(correct)}" data-qid="{qid}">'
    html += f'<p class="mb-2 text-sm font-semibold text-black">\u2753 {conditional_escape(question)}</p>'
    for i, choice in enumerate(choices):
        html += f'<label class="flex items-center gap-2 rounded px-3 py-1.5 text-sm text-[#424242] hover:bg-[#f0f0f0] cursor-pointer"><input type="radio" name="{qid}" value="{conditional_escape(choice)}" class="text-[#0067c0]"> {choice}</label>'
    html += f'<p class="quiz-feedback mt-2 hidden text-xs font-semibold"></p></div>'
    return html


def inline_format(text):
    def replacer(m):
        if m.group(2) is not None:
            return f"<strong>{m.group(2)}</strong>"
        if m.group(3) is not None:
            return f"<em>{m.group(3)}</em>"
        if m.group(4) is not None:
            return f"<code>{m.group(4)}</code>"
        if m.group(5) is not None:
            return _render_tip(m.group(5), m.group(6))
        if m.group(7) is not None:
            return _render_question(m.group(7), m.group(8))
        return m.group(0)
    return mark_safe(INLINE_RE.sub(replacer, conditional_escape(text)))


def resolve_content_file(relative_path):
    if not relative_path:
        return None
    path = (settings.BASE_DIR / relative_path).resolve()
    content_root = CONTENT_ROOT.resolve()
    if content_root not in path.parents and path != content_root:
        return None
    if not path.exists() or not path.is_file():
        return None
    return path


def read_stage_file(relative_path):
    path = resolve_content_file(relative_path)
    if not path:
        return ""
    return path.read_text(encoding="utf-8")


def load_json_file(relative_path):
    raw = read_stage_file(relative_path)
    if not raw:
        return {}
    return json.loads(raw)


def load_simple_yaml(path):
    if not path.exists():
        return {}
    data = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        if value.lower() in {"true", "false"}:
            data[key.strip()] = value.lower() == "true"
        else:
            try:
                data[key.strip()] = int(value)
            except ValueError:
                data[key.strip()] = value
    return data


def render_markdown(raw):
    lines = raw.splitlines()
    html_parts = []
    list_items = []
    in_code = False
    code_lines = []

    def flush_list():
        if list_items:
            html_parts.append(format_html("<ul class='list-disc space-y-1 pl-5'>{}</ul>", format_html_join("", "<li>{}</li>", ((item,) for item in list_items))))
            list_items.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                html_parts.append(format_html("<pre class='overflow-x-auto rounded-lg bg-[#111827] p-4 text-white'><code>{}</code></pre>", mark_safe(escape("\n".join(code_lines)))))
                code_lines = []
                in_code = False
            else:
                flush_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_list()
            continue
        if stripped.startswith("### "):
            flush_list()
            html_parts.append(format_html("<h4 class='mt-4 font-semibold text-[#9be62f]'>{}</h4>", inline_format(stripped[4:])))
        elif stripped.startswith("## "):
            flush_list()
            html_parts.append(format_html("<h3 class='mt-4 text-lg font-semibold text-[#9be62f]'>{}</h3>", inline_format(stripped[3:])))
        elif stripped.startswith("# "):
            flush_list()
            html_parts.append(format_html("<h2 class='text-xl font-semibold text-[#9be62f]'>{}</h2>", inline_format(stripped[2:])))
        elif stripped.startswith("- "):
            list_items.append(inline_format(stripped[2:]))
        else:
            flush_list()
            html_parts.append(format_html("<p>{}</p>", inline_format(stripped)))

    flush_list()
    if in_code:
        html_parts.append(format_html("<pre class='overflow-x-auto rounded-lg bg-[#111827] p-4 text-white'><code>{}</code></pre>", mark_safe(escape("\n".join(code_lines)))))

    return mark_safe("".join(str(part) for part in html_parts))


def render_json_stage(data):
    title = data.get("title", "Assessment")
    instructions = data.get("instructions", "")
    questions = data.get("questions", [])
    rows = [format_html("<h2 class='text-xl font-semibold text-black'>{}</h2>", title)]
    if instructions:
        rows.append(format_html("<p>{}</p>", instructions))
    if questions:
        rows.append(format_html("<ol class='list-decimal space-y-2 pl-5'>{}</ol>", format_html_join("", "<li>{}</li>", ((question.get("prompt", ""),) for question in questions))))
    return mark_safe("".join(str(row) for row in rows))


def render_yaml_stage(stage):
    path = resolve_content_file(stage.config_file)
    if not path:
        return ""
    metadata = load_simple_yaml(path)
    rows = [format_html("<h2 class='text-xl font-semibold text-black'>{}</h2>", metadata.get("title", "Sandbox"))]
    if metadata.get("description"):
        rows.append(format_html("<p>{}</p>", metadata["description"]))
    if metadata:
        rows.append(
            format_html(
                "<dl class='grid gap-3 sm:grid-cols-3'>{}</dl>",
                format_html_join(
                    "",
                    "<div class='rounded-lg bg-[#f7f7f7] p-3'><dt class='text-xs font-semibold text-[#5c5c5c]'>{}</dt><dd class='mt-1 font-semibold text-black'>{}</dd></div>",
                    ((key.replace("_", " ").title(), value) for key, value in metadata.items() if key not in {"title", "description"}),
                ),
            )
        )
    return mark_safe("".join(str(row) for row in rows))


def render_stage_content(stage):
    if stage.stage_type == stage.SANDBOX and stage.config_file:
        return render_yaml_stage(stage)
    if stage.stage_type == stage.ASSESSMENT and stage.content_file:
        return render_json_stage(load_json_file(stage.content_file))
    if stage.content_file:
        return render_markdown(read_stage_file(stage.content_file))
    if stage.content:
        return render_markdown(stage.content)
    return ""
