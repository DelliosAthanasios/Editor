import re

class CodeStructureParser:
    SUPPORTED_LANGUAGES = {
        # Existing (partial list for brevity, all from previous versions)
        "python", "c", "cpp", "java", "javascript", "typescript", "go", "ruby", "php",
        "csharp", "kotlin", "swift", "rust", "scala", "perl", "lua", "haskell",
        "dart", "objective-c", "shell", "r", "matlab", "groovy", "elixir", "fortran",

        # Markup & Data Languages
        "html", "xml", "json", "yaml",

        # Functional & Academic
        "ocaml", "fsharp", "erlang", "scheme", "commonlisp",

        # Scripting & Automation
        "powershell", "batch", "tcl",

        # Web & Domain-Specific
        "css", "sass", "scss", "sql", "graphql",

        # Legacy & Industry
        "cobol", "pascal", "ada", "vhdl", "verilog",

        # Others
        "julia", "crystal", "nim", "assembly", "prolog"
    }

    def __init__(self, language):
        self.language = language.lower()

    def parse(self, code):
        lang = self.language
        if lang == "html":
            return self._parse_html(code)
        elif lang == "xml":
            return self._parse_xml(code)
        elif lang == "json":
            return self._parse_json(code)
        elif lang == "yaml":
            return self._parse_yaml(code)
        elif lang == "ocaml":
            return self._parse_ocaml(code)
        elif lang == "fsharp":
            return self._parse_fsharp(code)
        elif lang == "erlang":
            return self._parse_erlang(code)
        elif lang == "scheme":
            return self._parse_scheme(code)
        elif lang == "commonlisp":
            return self._parse_commonlisp(code)
        elif lang == "powershell":
            return self._parse_powershell(code)
        elif lang == "batch":
            return self._parse_batch(code)
        elif lang == "tcl":
            return self._parse_tcl(code)
        elif lang == "css":
            return self._parse_css(code)
        elif lang in ("sass", "scss"):
            return self._parse_sass_scss(code)
        elif lang == "sql":
            return self._parse_sql(code)
        elif lang == "graphql":
            return self._parse_graphql(code)
        elif lang == "cobol":
            return self._parse_cobol(code)
        elif lang == "pascal":
            return self._parse_pascal(code)
        elif lang == "ada":
            return self._parse_ada(code)
        elif lang == "vhdl":
            return self._parse_vhdl(code)
        elif lang == "verilog":
            return self._parse_verilog(code)
        elif lang == "julia":
            return self._parse_julia(code)
        elif lang == "crystal":
            return self._parse_crystal(code)
        elif lang == "nim":
            return self._parse_nim(code)
        elif lang == "assembly":
            return self._parse_assembly(code)
        elif lang == "prolog":
            return self._parse_prolog(code)
        # fallback to previous (imported) parsers
        from code_explorer import CodeStructureParser as LegacyParser
        return LegacyParser(lang).parse(code)

    # --- Markup & Data Languages ---
    def _parse_html(self, code):
        tag_pattern = re.compile(r"<([a-zA-Z0-9]+)")
        tree = []
        for idx, line in enumerate(code.splitlines()):
            for match in tag_pattern.finditer(line):
                tag = match.group(1)
                tree.append({'type': 'tag', 'name': tag, 'line': idx+1})
        return tree

    def _parse_xml(self, code):
        tag_pattern = re.compile(r"<([a-zA-Z0-9:_-]+)")
        tree = []
        for idx, line in enumerate(code.splitlines()):
            for match in tag_pattern.finditer(line):
                tag = match.group(1)
                tree.append({'type': 'tag', 'name': tag, 'line': idx+1})
        return tree

    def _parse_json(self, code):
        key_pattern = re.compile(r'"([^"]+)"\s*:')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            for match in key_pattern.finditer(line):
                key = match.group(1)
                tree.append({'type': 'key', 'name': key, 'line': idx+1})
        return tree

    def _parse_yaml(self, code):
        key_pattern = re.compile(r'^(\s*)([A-Za-z0-9_\'"]+):')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = key_pattern.match(line)
            if match:
                key = match.group(2).strip("'\"")
                tree.append({'type': 'key', 'name': key, 'line': idx+1})
        return tree

    # --- Functional & Academic Languages ---
    def _parse_ocaml(self, code):
        type_pattern = re.compile(r'^\s*type\s+(\w+)')
        let_pattern = re.compile(r'^\s*let\s+(\w+)')
        module_pattern = re.compile(r'^\s*module\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if type_pattern.match(line):
                tree.append({'type': 'type', 'name': type_pattern.match(line).group(1), 'line': idx+1})
            elif let_pattern.match(line):
                tree.append({'type': 'let', 'name': let_pattern.match(line).group(1), 'line': idx+1})
            elif module_pattern.match(line):
                tree.append({'type': 'module', 'name': module_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_fsharp(self, code):
        let_pattern = re.compile(r'^\s*let\s+(\w+)')
        type_pattern = re.compile(r'^\s*type\s+(\w+)')
        module_pattern = re.compile(r'^\s*module\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if let_pattern.match(line):
                tree.append({'type': 'let', 'name': let_pattern.match(line).group(1), 'line': idx+1})
            elif type_pattern.match(line):
                tree.append({'type': 'type', 'name': type_pattern.match(line).group(1), 'line': idx+1})
            elif module_pattern.match(line):
                tree.append({'type': 'module', 'name': module_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_erlang(self, code):
        module_pattern = re.compile(r'-module\((\w+)\)')
        fun_pattern = re.compile(r'^(\w+)\((.*?)\)\s*->')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if module_pattern.search(line):
                tree.append({'type': 'module', 'name': module_pattern.search(line).group(1), 'line': idx+1})
            elif fun_pattern.match(line):
                tree.append({'type': 'function', 'name': fun_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_scheme(self, code):
        def_pattern = re.compile(r'^\s*\((define|lambda)\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = def_pattern.match(line)
            if match:
                tree.append({'type': match.group(1), 'name': match.group(2), 'line': idx+1})
        return tree

    def _parse_commonlisp(self, code):
        defun_pattern = re.compile(r'^\s*\(defun\s+(\w+)')
        defvar_pattern = re.compile(r'^\s*\(defvar\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if defun_pattern.match(line):
                tree.append({'type': 'function', 'name': defun_pattern.match(line).group(1), 'line': idx+1})
            elif defvar_pattern.match(line):
                tree.append({'type': 'variable', 'name': defvar_pattern.match(line).group(1), 'line': idx+1})
        return tree

    # --- Scripting & Automation ---
    def _parse_powershell(self, code):
        function_pattern = re.compile(r'function\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = function_pattern.search(line)
            if match:
                tree.append({'type': 'function', 'name': match.group(1), 'line': idx+1})
        return tree

    def _parse_batch(self, code):
        label_pattern = re.compile(r'^:([\w\d_]+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = label_pattern.match(line)
            if match:
                tree.append({'type': 'label', 'name': match.group(1), 'line': idx+1})
        return tree

    def _parse_tcl(self, code):
        proc_pattern = re.compile(r'^\s*proc\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = proc_pattern.match(line)
            if match:
                tree.append({'type': 'procedure', 'name': match.group(1), 'line': idx+1})
        return tree

    # --- Web & Domain-Specific ---
    def _parse_css(self, code):
        selector_pattern = re.compile(r'^([.#]?\w[\w\-]*)\s*\{')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = selector_pattern.match(line)
            if match:
                tree.append({'type': 'selector', 'name': match.group(1), 'line': idx+1})
        return tree

    def _parse_sass_scss(self, code):
        selector_pattern = re.compile(r'^([.#]?\w[\w\-]*)\s*\{')
        var_pattern = re.compile(r'^\s*\$(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if var_pattern.match(line):
                tree.append({'type': 'variable', 'name': var_pattern.match(line).group(1), 'line': idx+1})
            elif selector_pattern.match(line):
                tree.append({'type': 'selector', 'name': selector_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_sql(self, code):
        table_pattern = re.compile(r'CREATE\s+TABLE\s+(\w+)', re.IGNORECASE)
        proc_pattern = re.compile(r'CREATE\s+(PROCEDURE|FUNCTION)\s+(\w+)', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if table_pattern.search(line):
                tree.append({'type': 'table', 'name': table_pattern.search(line).group(1), 'line': idx+1})
            elif proc_pattern.search(line):
                tree.append({'type': proc_pattern.search(line).group(1).lower(), 'name': proc_pattern.search(line).group(2), 'line': idx+1})
        return tree

    def _parse_graphql(self, code):
        type_pattern = re.compile(r'^\s*type\s+(\w+)')
        query_pattern = re.compile(r'^\s*query\s+(\w+)')
        mutation_pattern = re.compile(r'^\s*mutation\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if type_pattern.match(line):
                tree.append({'type': 'type', 'name': type_pattern.match(line).group(1), 'line': idx+1})
            elif query_pattern.match(line):
                tree.append({'type': 'query', 'name': query_pattern.match(line).group(1), 'line': idx+1})
            elif mutation_pattern.match(line):
                tree.append({'type': 'mutation', 'name': mutation_pattern.match(line).group(1), 'line': idx+1})
        return tree

    # --- Legacy & Industry ---
    def _parse_cobol(self, code):
        division_pattern = re.compile(r'^\s*(\w+)\s+DIVISION\.', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = division_pattern.match(line)
            if match:
                tree.append({'type': 'division', 'name': match.group(1).capitalize(), 'line': idx+1})
        return tree

    def _parse_pascal(self, code):
        program_pattern = re.compile(r'^\s*program\s+(\w+)', re.IGNORECASE)
        procedure_pattern = re.compile(r'^\s*procedure\s+(\w+)', re.IGNORECASE)
        function_pattern = re.compile(r'^\s*function\s+(\w+)', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if program_pattern.match(line):
                tree.append({'type': 'program', 'name': program_pattern.match(line).group(1), 'line': idx+1})
            elif procedure_pattern.match(line):
                tree.append({'type': 'procedure', 'name': procedure_pattern.match(line).group(1), 'line': idx+1})
            elif function_pattern.match(line):
                tree.append({'type': 'function', 'name': function_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_ada(self, code):
        procedure_pattern = re.compile(r'^\s*procedure\s+(\w+)', re.IGNORECASE)
        function_pattern = re.compile(r'^\s*function\s+(\w+)', re.IGNORECASE)
        package_pattern = re.compile(r'^\s*package\s+(\w+)', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if procedure_pattern.match(line):
                tree.append({'type': 'procedure', 'name': procedure_pattern.match(line).group(1), 'line': idx+1})
            elif function_pattern.match(line):
                tree.append({'type': 'function', 'name': function_pattern.match(line).group(1), 'line': idx+1})
            elif package_pattern.match(line):
                tree.append({'type': 'package', 'name': package_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_vhdl(self, code):
        entity_pattern = re.compile(r'^\s*entity\s+(\w+)', re.IGNORECASE)
        architecture_pattern = re.compile(r'^\s*architecture\s+(\w+)', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if entity_pattern.match(line):
                tree.append({'type': 'entity', 'name': entity_pattern.match(line).group(1), 'line': idx+1})
            elif architecture_pattern.match(line):
                tree.append({'type': 'architecture', 'name': architecture_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_verilog(self, code):
        module_pattern = re.compile(r'^\s*module\s+(\w+)', re.IGNORECASE)
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if module_pattern.match(line):
                tree.append({'type': 'module', 'name': module_pattern.match(line).group(1), 'line': idx+1})
        return tree

    # --- Others ---
    def _parse_julia(self, code):
        function_pattern = re.compile(r'^\s*function\s+(\w+)')
        module_pattern = re.compile(r'^\s*module\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if function_pattern.match(line):
                tree.append({'type': 'function', 'name': function_pattern.match(line).group(1), 'line': idx+1})
            elif module_pattern.match(line):
                tree.append({'type': 'module', 'name': module_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_crystal(self, code):
        class_pattern = re.compile(r'^\s*class\s+(\w+)')
        module_pattern = re.compile(r'^\s*module\s+(\w+)')
        def_pattern = re.compile(r'^\s*def\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if class_pattern.match(line):
                tree.append({'type': 'class', 'name': class_pattern.match(line).group(1), 'line': idx+1})
            elif module_pattern.match(line):
                tree.append({'type': 'module', 'name': module_pattern.match(line).group(1), 'line': idx+1})
            elif def_pattern.match(line):
                tree.append({'type': 'function', 'name': def_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_nim(self, code):
        proc_pattern = re.compile(r'^\s*proc\s+(\w+)')
        type_pattern = re.compile(r'^\s*type\s+(\w+)')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            if proc_pattern.match(line):
                tree.append({'type': 'proc', 'name': proc_pattern.match(line).group(1), 'line': idx+1})
            elif type_pattern.match(line):
                tree.append({'type': 'type', 'name': type_pattern.match(line).group(1), 'line': idx+1})
        return tree

    def _parse_assembly(self, code):
        label_pattern = re.compile(r'^\s*([\.\w]+):')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = label_pattern.match(line)
            if match:
                tree.append({'type': 'label', 'name': match.group(1), 'line': idx+1})
        return tree

    def _parse_prolog(self, code):
        predicate_pattern = re.compile(r'^(\w+)\s*\(')
        tree = []
        for idx, line in enumerate(code.splitlines()):
            match = predicate_pattern.match(line)
            if match:
                tree.append({'type': 'predicate', 'name': match.group(1), 'line': idx+1})
        return tree
