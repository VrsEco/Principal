import pathlib

text = pathlib.Path("templates/grv_process_detail.html").read_text(encoding="utf8")
needle = "  const popManager = document.querySelector('[data-pop-manager]');"
start = text.find(needle)
if start == -1:
    raise SystemExit("not found")
end = text.find("    fetchActivities();", start)
if end == -1:
    raise SystemExit("fetch not found")
end = text.find("\n", end)
print(text[start:end])
