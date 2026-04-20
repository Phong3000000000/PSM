#!/usr/bin/env python3
"""Build a structured JSON map for an Odoo module."""

from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "structure"
DETAILS_DIR = OUTPUT_DIR / "details"

SKIP_DIRS = {"__pycache__", ".git", "structure"}
TEXT_EXTENSIONS = {".py", ".xml", ".csv", ".md", ".txt"}
MODEL_ID_PREFIX = "model_"


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def rel_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def file_bucket(path: Path) -> str:
    parts = path.relative_to(ROOT).parts
    if len(parts) == 1:
        if path.name == "__manifest__.py":
            return "manifest"
        if path.suffix == ".py":
            return "python"
        if path.suffix == ".md":
            return "docs"
        return "root"
    top = parts[0]
    return {
        "models": "models",
        "views": "views",
        "security": "security",
        "data": "data",
        "controllers": "controllers",
        "reports": "reports",
        "notes": "notes",
        "office": "office",
    }.get(top, top)


def summarize_files(paths: list[str], limit: int = 5) -> str:
    if not paths:
        return ""
    if len(paths) <= limit:
        return ", ".join(paths)
    head = ", ".join(paths[:limit])
    return f"{head}, +{len(paths) - limit} more"


def make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [make_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def node_to_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = node_to_value(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.List):
        return [node_to_value(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return [node_to_value(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            node_to_value(key): node_to_value(value)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Call):
        func = node_to_value(node.func)
        args = [node_to_value(arg) for arg in node.args]
        keywords = {kw.arg: node_to_value(kw.value) for kw in node.keywords if kw.arg}
        return {"call": func, "args": args, "keywords": keywords}
    if isinstance(node, ast.Lambda):
        return "lambda"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = node_to_value(node.operand)
        return -operand if isinstance(operand, (int, float)) else operand
    return ast.dump(node, include_attributes=False)


def short_text(value: Any, limit: int = 180) -> str:
    text = ""
    if isinstance(value, str):
        text = value
    elif value is not None:
        text = json.dumps(make_json_safe(value), ensure_ascii=False)
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def parse_manifest(path: Path) -> dict[str, Any]:
    source = read_text(path)
    cleaned = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    ).strip()
    manifest = ast.literal_eval(cleaned)
    return make_json_safe(manifest)


def parse_python_file(path: Path) -> dict[str, Any]:
    source = read_text(path)
    tree = ast.parse(source, filename=str(path))
    classes = []
    routes = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        class_info: dict[str, Any] = {
            "python_class": node.name,
            "description": ast.get_docstring(node),
            "model": None,
            "inherit": None,
            "order": None,
            "rec_name": None,
            "fields": [],
            "methods": [],
        }

        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
                if not targets:
                    continue
                name = targets[0]
                value = node_to_value(stmt.value)
                if name == "_name":
                    class_info["model"] = value
                elif name == "_inherit":
                    class_info["inherit"] = value
                elif name == "_description":
                    class_info["description"] = value
                elif name == "_order":
                    class_info["order"] = value
                elif name == "_rec_name":
                    class_info["rec_name"] = value
                elif isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Attribute) and isinstance(
                        call.func.value, ast.Name
                    ) and call.func.value.id == "fields":
                        field_type = call.func.attr
                        field_info = {
                            "name": name,
                            "type": field_type,
                            "string": None,
                            "comodel": None,
                            "required": False,
                            "readonly": False,
                            "store": None,
                            "related": None,
                            "compute": None,
                            "selection": None,
                            "default": None,
                            "tracking": None,
                            "help": None,
                        }
                        if call.args and isinstance(call.args[0], ast.Constant) and isinstance(
                            call.args[0].value, str
                        ):
                            field_info["comodel"] = call.args[0].value
                        for kw in call.keywords:
                            if not kw.arg:
                                continue
                            value = node_to_value(kw.value)
                            if kw.arg in field_info:
                                field_info[kw.arg] = value
                            elif kw.arg == "string":
                                field_info["string"] = value
                        if field_type == "Selection" and call.args:
                            field_info["selection"] = short_text(node_to_value(call.args[0]), 120)
                        class_info["fields"].append(make_json_safe(field_info))
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [node_to_value(dec) for dec in stmt.decorator_list]
                method_type = "method"
                if stmt.name.startswith("action_"):
                    method_type = "action"
                elif any("api.depends" in str(dec) for dec in decorators) or stmt.name.startswith(
                    "_compute_"
                ):
                    method_type = "compute"
                elif any("api.onchange" in str(dec) for dec in decorators) or stmt.name.startswith(
                    "_onchange_"
                ):
                    method_type = "onchange"
                elif any("api.constrains" in str(dec) for dec in decorators):
                    method_type = "constraint"
                elif stmt.name in {"create", "write", "unlink", "default_get", "copy"}:
                    method_type = "override"
                elif stmt.name.startswith("_"):
                    method_type = "helper"

                method_info = {
                    "name": stmt.name,
                    "type": method_type,
                    "decorators": decorators,
                    "summary": ast.get_docstring(stmt) or method_type.replace("_", " "),
                }
                class_info["methods"].append(make_json_safe(method_info))

                for dec in stmt.decorator_list:
                    dec_value = node_to_value(dec)
                    if isinstance(dec_value, dict) and dec_value.get("call") == "http.route":
                        routes.append(
                            {
                                "method": stmt.name,
                                "route": dec_value.get("args", []),
                                "options": dec_value.get("keywords", {}),
                            }
                        )

        model = class_info["model"]
        inherit = class_info["inherit"]
        if model and not inherit:
            class_info["kind"] = "new_model"
        elif model and inherit:
            class_info["kind"] = "new_model_with_inherit"
        elif inherit:
            class_info["kind"] = "inherit_only"
        else:
            class_info["kind"] = "python_class"

        if not class_info["description"]:
            if model:
                class_info["description"] = f"Defines {model} in {rel_path(path)}."
            elif inherit:
                class_info["description"] = f"Extends {inherit} in {rel_path(path)}."
            else:
                class_info["description"] = f"Python helper class {node.name}."

        classes.append(make_json_safe(class_info))

    summary_bits = []
    model_names = [item["model"] or item["inherit"] for item in classes if item.get("model") or item.get("inherit")]
    if model_names:
        summary_bits.append(f"models: {', '.join(model_names[:4])}")
    if classes:
        field_total = sum(len(item["fields"]) for item in classes)
        action_total = sum(1 for item in classes for method in item["methods"] if method["type"] == "action")
        summary_bits.append(f"{len(classes)} classes")
        summary_bits.append(f"{field_total} fields")
        if action_total:
            summary_bits.append(f"{action_total} actions")
    return {
        "file": rel_path(path),
        "type": "python",
        "bucket": file_bucket(path),
        "summary": "; ".join(summary_bits) if summary_bits else "Python source file.",
        "classes": classes,
        "routes": routes,
    }


def parse_access_csv(path: Path) -> dict[str, Any]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("id"):
                continue
            rows.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "model_id": row.get("model_id:id"),
                    "group_id": row.get("group_id:id"),
                    "model": None,
                    "perm_read": row.get("perm_read") == "1",
                    "perm_write": row.get("perm_write") == "1",
                    "perm_create": row.get("perm_create") == "1",
                    "perm_unlink": row.get("perm_unlink") == "1",
                }
            )
    return {
        "file": rel_path(path),
        "type": "security_csv",
        "bucket": file_bucket(path),
        "summary": f"{len(rows)} access rules",
        "access_rules": rows,
    }


def parse_xml_file(path: Path) -> dict[str, Any]:
    source = read_text(path)
    wrapped = source.strip()
    root = ET.fromstring(wrapped)
    records = []
    views = []
    actions = []
    menus = []
    templates = []
    functions = []
    referenced_models = set()

    for elem in root.iter():
        if elem.tag == "record":
            record_info = {
                "id": elem.attrib.get("id"),
                "model": elem.attrib.get("model"),
                "fields": {},
            }
            for field in elem.findall("field"):
                field_name = field.attrib.get("name")
                if not field_name:
                    continue
                value = (field.text or "").strip()
                if field.attrib.get("ref"):
                    value = {"ref": field.attrib["ref"]}
                elif field.attrib.get("eval"):
                    value = {"eval": field.attrib["eval"]}
                record_info["fields"][field_name] = value
            records.append(record_info)
            model_name = elem.attrib.get("model")
            if model_name:
                referenced_models.add(model_name)

            if elem.attrib.get("model") == "ir.ui.view":
                view_model = record_info["fields"].get("model")
                inherit_ref = record_info["fields"].get("inherit_id", {})
                view_info = {
                    "id": record_info["id"],
                    "model": view_model,
                    "name": record_info["fields"].get("name"),
                    "inherit_id": inherit_ref.get("ref") if isinstance(inherit_ref, dict) else inherit_ref,
                    "file": rel_path(path),
                }
                views.append(view_info)
                if isinstance(view_model, str):
                    referenced_models.add(view_model)
            elif elem.attrib.get("model") == "ir.actions.act_window":
                res_model = record_info["fields"].get("res_model")
                action_info = {
                    "id": record_info["id"],
                    "name": record_info["fields"].get("name"),
                    "res_model": res_model,
                    "view_mode": record_info["fields"].get("view_mode"),
                    "domain": record_info["fields"].get("domain"),
                    "file": rel_path(path),
                }
                actions.append(action_info)
                if isinstance(res_model, str):
                    referenced_models.add(res_model)
            elif elem.attrib.get("model") == "ir.rule":
                rule_model = record_info["fields"].get("model_id")
                domain = record_info["fields"].get("domain_force")
                functions.append(
                    {
                        "kind": "record_rule",
                        "id": record_info["id"],
                        "name": record_info["fields"].get("name"),
                        "model_ref": rule_model,
                        "domain": domain,
                    }
                )
        elif elem.tag == "menuitem":
            menu_info = {
                "id": elem.attrib.get("id"),
                "name": elem.attrib.get("name"),
                "parent": elem.attrib.get("parent"),
                "action": elem.attrib.get("action"),
                "groups": elem.attrib.get("groups"),
                "file": rel_path(path),
            }
            menus.append(menu_info)
        elif elem.tag == "template":
            template_info = {
                "id": elem.attrib.get("id"),
                "name": elem.attrib.get("name"),
                "inherit_id": elem.attrib.get("inherit_id"),
                "file": rel_path(path),
            }
            templates.append(template_info)
        elif elem.tag == "function":
            functions.append(
                {
                    "kind": "function",
                    "model": elem.attrib.get("model"),
                    "name": elem.attrib.get("name"),
                }
            )
            if elem.attrib.get("model"):
                referenced_models.add(elem.attrib["model"])

    bits = []
    if views:
        bits.append(f"{len(views)} views")
    if actions:
        bits.append(f"{len(actions)} actions")
    if menus:
        bits.append(f"{len(menus)} menus")
    if templates:
        bits.append(f"{len(templates)} templates")
    if functions:
        bits.append(f"{len(functions)} functions/rules")

    return {
        "file": rel_path(path),
        "type": "xml",
        "bucket": file_bucket(path),
        "summary": ", ".join(bits) if bits else "XML data file.",
        "records": make_json_safe(records),
        "views": make_json_safe(views),
        "actions": make_json_safe(actions),
        "menus": make_json_safe(menus),
        "templates": make_json_safe(templates),
        "functions": make_json_safe(functions),
        "referenced_models": sorted(referenced_models),
    }


def csv_model_id_to_model(value: str | None, known_models: set[str]) -> str | None:
    if not value:
        return None
    for model_name in sorted(known_models, key=len, reverse=True):
        if value.endswith(model_name.replace(".", "_")):
            return model_name
    if value.startswith(MODEL_ID_PREFIX):
        remainder = value[len(MODEL_ID_PREFIX) :]
        return remainder.replace("_", ".")
    return value


def collect_files() -> list[Path]:
    results = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        results.append(path)
    return sorted(results)


def build_relations(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    model_to_file = {}

    for detail in details:
        if detail["type"] != "python":
            continue
        for cls in detail.get("classes", []):
            model_name = cls.get("model") or cls.get("inherit")
            if isinstance(model_name, str):
                model_to_file.setdefault(model_name, detail["file"])

    for detail in details:
        if detail["type"] == "python":
            for cls in detail.get("classes", []):
                model_name = cls.get("model")
                inherit_value = cls.get("inherit")
                if isinstance(inherit_value, str):
                    relations.append(
                        {
                            "from": detail["file"],
                            "to_model": inherit_value,
                            "type": "inherits_model",
                            "model": model_name or inherit_value,
                        }
                    )
                elif isinstance(inherit_value, list):
                    for item in inherit_value:
                        if isinstance(item, str):
                            relations.append(
                                {
                                    "from": detail["file"],
                                    "to_model": item,
                                    "type": "inherits_model",
                                    "model": model_name or item,
                                }
                            )
                for field in cls.get("fields", []):
                    comodel = field.get("comodel")
                    if isinstance(comodel, str) and "." in comodel:
                        relations.append(
                            {
                                "from": detail["file"],
                                "to_model": comodel,
                                "type": "field_relation",
                                "field": field.get("name"),
                            }
                        )
        elif detail["type"] == "xml":
            for view in detail.get("views", []):
                model_name = view.get("model")
                if isinstance(model_name, str):
                    relations.append(
                        {
                            "from": detail["file"],
                            "to": model_to_file.get(model_name),
                            "to_model": model_name,
                            "type": "uses_model",
                            "view_id": view.get("id"),
                        }
                    )
            for action in detail.get("actions", []):
                model_name = action.get("res_model")
                if isinstance(model_name, str):
                    relations.append(
                        {
                            "from": detail["file"],
                            "to": model_to_file.get(model_name),
                            "to_model": model_name,
                            "type": "opens_model",
                            "action_id": action.get("id"),
                        }
                    )
            for menu in detail.get("menus", []):
                if menu.get("action"):
                    relations.append(
                        {
                            "from": detail["file"],
                            "to_action": menu.get("action"),
                            "type": "menu_action",
                            "menu_id": menu.get("id"),
                        }
                    )
        elif detail["type"] == "security_csv":
            for rule in detail.get("access_rules", []):
                model_name = rule.get("model")
                relations.append(
                    {
                        "from": detail["file"],
                        "to": model_to_file.get(model_name),
                        "to_model": model_name,
                        "type": "grants_access",
                        "group": rule.get("group_id"),
                    }
                )

    deduped = []
    seen = set()
    for item in relations:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def build_feature_summary(module_map: dict[str, Any]) -> list[str]:
    features = []
    model_names = {item["model"] for item in module_map["models"] if item.get("model")}
    if "x_psm_recruitment_request" in model_names:
        features.append("Recruitment request workflow with approval integration and job publishing.")
    if "x_psm_recruitment_plan" in model_names or "x_psm_recruitment_batch" in model_names:
        features.append("Recruitment planning and batch execution flows for office hiring.")
    if any(model in model_names for model in {"x_psm_applicant_evaluation", "hr.applicant"}):
        features.append("Extended applicant pipeline with interview scheduling, survey, and evaluation support.")
    if module_map["counts"].get("controllers"):
        features.append("Portal and website controllers for recruitment pages and application flow.")
    if module_map["counts"].get("security"):
        features.append("Dedicated recruitment groups, access rules, and security bridges.")
    if module_map["counts"].get("data"):
        features.append("Seed data for sequences, stages, approval categories, mail templates, cron jobs, and surveys.")
    return features


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = parse_manifest(ROOT / "__manifest__.py")
    files = collect_files()
    detail_objects = []
    structure_map: dict[str, list[str]] = defaultdict(list)
    counts = Counter()

    for path in files:
        relative = rel_path(path)
        bucket = file_bucket(path)
        structure_map[bucket].append(relative)
        counts[bucket] += 1

        detail: dict[str, Any]
        if path.suffix == ".py" and path.name != "__manifest__.py":
            detail = parse_python_file(path)
        elif path.suffix == ".xml":
            detail = parse_xml_file(path)
        elif path.suffix == ".csv" and path.name == "ir.model.access.csv":
            detail = parse_access_csv(path)
        else:
            text = read_text(path) if path.suffix in TEXT_EXTENSIONS else ""
            detail = {
                "file": relative,
                "type": "document" if path.suffix in {".md", ".txt"} else "file",
                "bucket": bucket,
                "summary": short_text(text, 160) if text else f"{path.suffix or 'binary'} file",
            }
        detail_objects.append(detail)

        detail_target = DETAILS_DIR / (relative.replace("/", "__") + ".json")
        detail_target.parent.mkdir(parents=True, exist_ok=True)
        detail_target.write_text(
            json.dumps(make_json_safe(detail), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    known_models = {
        cls.get("model")
        for detail in detail_objects
        if detail["type"] == "python"
        for cls in detail.get("classes", [])
        if isinstance(cls.get("model"), str)
    }

    for detail in detail_objects:
        if detail["type"] != "security_csv":
            continue
        for rule in detail.get("access_rules", []):
            rule["model"] = csv_model_id_to_model(rule.get("model_id"), known_models)
        detail_target = DETAILS_DIR / (detail["file"].replace("/", "__") + ".json")
        detail_target.write_text(
            json.dumps(make_json_safe(detail), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    relations = build_relations(detail_objects)

    model_entries = []
    view_entries = []
    controller_entries = []
    security_entries = []
    data_entries = []

    for detail in detail_objects:
        if detail["type"] == "python":
            if detail["bucket"] == "models":
                for cls in detail.get("classes", []):
                    model_entries.append(
                        {
                            "file": detail["file"],
                            "python_class": cls.get("python_class"),
                            "model": cls.get("model"),
                            "inherit": cls.get("inherit"),
                            "kind": cls.get("kind"),
                            "description": cls.get("description"),
                            "field_count": len(cls.get("fields", [])),
                            "method_count": len(cls.get("methods", [])),
                            "important_fields": [field["name"] for field in cls.get("fields", [])[:12]],
                            "actions": [
                                method["name"]
                                for method in cls.get("methods", [])
                                if method.get("type") == "action"
                            ][:12],
                        }
                    )
            elif detail["bucket"] == "controllers":
                controller_entries.append(
                    {
                        "file": detail["file"],
                        "summary": detail["summary"],
                        "routes": detail.get("routes", []),
                    }
                )
        elif detail["type"] == "xml":
            if detail["bucket"] == "views":
                for view in detail.get("views", []):
                    view_entries.append(view)
            elif detail["bucket"] == "security":
                security_entries.append(
                    {
                        "file": detail["file"],
                        "summary": detail["summary"],
                        "record_rules": [
                            item for item in detail.get("functions", []) if item.get("kind") == "record_rule"
                        ],
                    }
                )
            elif detail["bucket"] == "data":
                data_entries.append(
                    {
                        "file": detail["file"],
                        "summary": detail["summary"],
                        "record_count": len(detail.get("records", [])),
                        "function_count": len(detail.get("functions", [])),
                    }
                )
        elif detail["type"] == "security_csv":
            security_entries.append(
                {
                    "file": detail["file"],
                    "summary": detail["summary"],
                    "access_rules": detail.get("access_rules", []),
                }
            )

    module_map = {
        "module_name": ROOT.name,
        "module_path": str(ROOT),
        "manifest": manifest,
        "counts": dict(counts),
        "structure": {bucket: sorted(paths) for bucket, paths in sorted(structure_map.items())},
        "models": model_entries,
        "views": view_entries,
        "security": security_entries,
        "controllers": controller_entries,
        "data": data_entries,
        "relations": relations,
        "feature_summary": [],
        "detail_index": [
            {
                "file": detail["file"],
                "detail_json": f"details/{detail['file'].replace('/', '__')}.json",
                "type": detail["type"],
                "bucket": detail["bucket"],
                "summary": detail["summary"],
            }
            for detail in detail_objects
        ],
    }
    module_map["feature_summary"] = build_feature_summary(module_map)

    overview = OUTPUT_DIR / "module_map.json"
    overview.write_text(
        json.dumps(make_json_safe(module_map), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    stats = {
        "module_name": ROOT.name,
        "detail_file_count": len(detail_objects),
        "relation_count": len(relations),
        "top_buckets": counts.most_common(),
        "model_count": len(model_entries),
        "view_count": len(view_entries),
        "security_file_count": len(security_entries),
        "controller_file_count": len(controller_entries),
        "sample_files": summarize_files([detail["file"] for detail in detail_objects[:10]], limit=10),
    }
    (OUTPUT_DIR / "module_map_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
