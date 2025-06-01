import re

class CodeStructureParser:
    def __init__(self, language):
        self.language = language.lower()

    def parse(self, code):
        if self.language == "python":
            return self._parse_python(code)
        elif self.language in ("c", "cpp", "c++"):
            return self._parse_c_cpp(code)
        elif self.language == "java":
            return self._parse_java(code)
        else:
            return []

    def _parse_python(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*class\s+(\w+)(\((.*?)\))?:")
        func_pattern = re.compile(r"^\s*def\s+(\w+)\s*\((.*?)\)")
        variable_pattern = re.compile(r"^\s*(\w+)\s*[:=]\s*([^=]*)")
        type_hint_pattern = re.compile(r"^\s*(\w+)\s*:\s*([\w\[\], ]+)")
        lines = code.splitlines()
        parents = []
        indent_stack = []
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = variable_pattern.match(line)
            type_hint_match = type_hint_pattern.match(line)
            indent = len(line) - len(line.lstrip())
            while indent_stack and indent < indent_stack[-1][0]:
                indent_stack.pop()
                if parents:
                    parents.pop()
            if class_match:
                class_name = class_match.group(1)
                inherits = class_match.group(3) or ""
                node = {'type': 'class', 'name': class_name, 'inherits': inherits, 'children': [], 'line': idx+1, 'members': []}
                if parents:
                    parents[-1]['children'].append(node)
                else:
                    tree.append(node)
                parents.append(node)
                indent_stack.append((indent, node))
            elif func_match:
                func_name = func_match.group(1)
                params = func_match.group(2).replace("self,", "").replace("self", "").strip()
                node = {'type': 'function', 'name': func_name, 'params': params, 'children': [], 'line': idx+1, 'members': []}
                if parents and indent > 0:
                    parents[-1]['children'].append(node)
                    if parents[-1]['type'] == 'class':
                        parents[-1]['members'].append(func_name)
                else:
                    tree.append(node)
                parents.append(node)
                indent_stack.append((indent, node))
            elif var_match:
                var_name = var_match.group(1)
                var_type = type_hint_match.group(2).strip() if type_hint_match else ""
                node = {'type': 'variable', 'name': var_name, 'vtype': var_type, 'line': idx+1}
                if parents and indent > 0:
                    parents[-1]['children'].append(node)
                    if parents[-1]['type'] == 'class':
                        parents[-1]['members'].append(var_name)
                else:
                    tree.append(node)
        return tree

    def _parse_c_cpp(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*(class|struct)\s+(\w+)(\s*:\s*([\w\s,]+))?")
        func_pattern = re.compile(r"^\s*([\w\<\>\*\&\s]+)\s+(\w+)\s*\(([^)]*)\)\s*\{?")
        var_pattern = re.compile(r"^\s*([\w\<\>\*\&]+)\s+(\w+)\s*(=\s*[^;]+)?;")
        lines = code.splitlines()
        current_class = None
        inside_class = False
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = var_pattern.match(line)
            if class_match:
                class_name = class_match.group(2)
                inherits = class_match.group(4) or ""
                node = {'type': 'class', 'name': class_name, 'inherits': inherits, 'children': [], 'line': idx+1, 'members': []}
                tree.append(node)
                current_class = node
                inside_class = True
            elif func_match:
                ret_type = func_match.group(1).strip()
                func_name = func_match.group(2)
                params = func_match.group(3).strip()
                node = {'type': 'function', 'name': func_name, 'ret_type': ret_type, 'params': params, 'children': [], 'line': idx+1, 'members': []}
                if inside_class and current_class:
                    current_class['children'].append(node)
                    current_class['members'].append(func_name)
                else:
                    tree.append(node)
            elif var_match:
                var_type = var_match.group(1).strip()
                var_name = var_match.group(2)
                node = {'type': 'variable', 'name': var_name, 'vtype': var_type, 'line': idx+1}
                if inside_class and current_class:
                    current_class['children'].append(node)
                    current_class['members'].append(var_name)
                else:
                    tree.append(node)
            if "};" in line:
                inside_class = False
                current_class = None
        return tree

    def _parse_java(self, code):
        tree = []
        class_pattern = re.compile(r"^\s*(public\s+)?(class|interface)\s+(\w+)(\s+extends\s+(\w+))?")
        func_pattern = re.compile(r"^\s*(public|protected|private|static|\s)+([\w\<\>\[\]]+)\s+(\w+)\s*\(([^)]*)\)\s*\{?")
        var_pattern = re.compile(r"^\s*(public|protected|private|static|\s)+([\w\<\>\[\]]+)\s+(\w+)\s*(=\s*[^;]+)?;")
        lines = code.splitlines()
        current_class = None
        inside_class = False
        for idx, line in enumerate(lines):
            class_match = class_pattern.match(line)
            func_match = func_pattern.match(line)
            var_match = var_pattern.match(line)
            if class_match:
                class_name = class_match.group(3)
                inherits = class_match.group(5) or ""
                node = {'type': 'class', 'name': class_name, 'inherits': inherits, 'children': [], 'line': idx+1, 'members': []}
                tree.append(node)
                current_class = node
                inside_class = True
            elif func_match:
                ret_type = func_match.group(2).strip()
                func_name = func_match.group(3)
                params = func_match.group(4).strip()
                node = {'type': 'function', 'name': func_name, 'ret_type': ret_type, 'params': params, 'children': [], 'line': idx+1, 'members': []}
                if inside_class and current_class:
                    current_class['children'].append(node)
                    current_class['members'].append(func_name)
                else:
                    tree.append(node)
            elif var_match:
                var_type = var_match.group(2)
                var_name = var_match.group(3)
                node = {'type': 'variable', 'name': var_name, 'vtype': var_type, 'line': idx+1}
                if inside_class and current_class:
                    current_class['children'].append(node)
                    current_class['members'].append(var_name)
                else:
                    tree.append(node)
            if "}" in line and inside_class:
                inside_class = False
                current_class = None
        return tree

