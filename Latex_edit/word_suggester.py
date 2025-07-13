LATEX_COMMANDS = [
    "\\begin", "\\end", "\\section", "\\subsection", "\\textbf", "\\textit", "\\item", "\\documentclass", "\\usepackage", "\\title", "\\author", "\\date", "\\maketitle", "\\tableofcontents", "\\chapter", "\\label", "\\ref", "\\cite", "\\includegraphics", "\\footnote", "\\emph", "\\frac", "\\sqrt", "\\sum", "\\int", "\\left", "\\right", "\\include", "\\input", "\\bibliography", "\\bibliographystyle"
]

def suggest_latex_commands(prefix):
    """Return a list of LaTeX commands that start with the given prefix."""
    return [cmd for cmd in LATEX_COMMANDS if cmd.startswith(prefix)] 