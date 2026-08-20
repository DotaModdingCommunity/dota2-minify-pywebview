import os
import re
import xml.etree.ElementTree as ET
from typing import Any

import defusedxml.ElementTree as dET
from core import log

TAG_CHAR = r"[a-zA-Z0-9_:-]"
ID_CHAR = r"[a-zA-Z0-9_:-]"
CLASS_CHAR = r"[a-zA-Z0-9_:.-]"
ATTR_CHAR = r"[a-zA-Z0-9_:.-]"
SELECTOR_PATTERN = (
    rf"^({TAG_CHAR}+)?(?:#({ID_CHAR}+))?((?:\.{CLASS_CHAR}+)*)((?:\[{ATTR_CHAR}+(?:=['\"]?[^'\"\]]+['\"]?)?\])*)$"
)
ATTRIBUTE_PATTERN = r"\[([a-zA-Z0-9_:.-]+)(?:=(['\"]?)([^'\"\]]*)\2)?\]"


SELECTOR_RE = re.compile(SELECTOR_PATTERN)
ATTRIBUTE_RE = re.compile(ATTRIBUTE_PATTERN)


def find_by_selector(root: ET.Element, selector: str) -> ET.Element | None:
    if not selector:
        return None
    match = SELECTOR_RE.match(selector)
    if not match:
        return None

    tag_name, element_id, classes_str, attrs_str = match.groups()
    target_classes = classes_str.replace(".", " ").split()
    target_attrs = {}
    if attrs_str:
        attr_matches = ATTRIBUTE_RE.findall(attrs_str)
        for m in attr_matches:
            k = m[0]
            v = m[2] if m[1] or m[2] else None
            target_attrs[k] = v

    def matches(elem: ET.Element) -> bool:
        if tag_name and elem.tag != tag_name:
            return False
        if element_id and elem.get("id") != element_id:
            return False
        if target_classes:
            elem_classes = (elem.get("class") or "").split()
            if not all(cls in elem_classes for cls in target_classes):
                return False
        if target_attrs:
            if not all((k in elem.attrib) if v is None else elem.get(k) == v for k, v in target_attrs.items()):
                return False
        return True

    if matches(root):
        return root
    for elem in root.iter():
        if elem == root:
            continue
        if matches(elem):
            return elem
    return None


def find_with_parent_by_selector(root: ET.Element, selector: str) -> tuple[ET.Element | None, ET.Element | None]:
    if not selector:
        return None, None
    match = SELECTOR_RE.match(selector)
    if not match:
        return None, None

    tag_name, element_id, classes_str, attrs_str = match.groups()
    target_classes = classes_str.replace(".", " ").split()
    target_attrs = {}
    if attrs_str:
        attr_matches = ATTRIBUTE_RE.findall(attrs_str)
        for m in attr_matches:
            k = m[0]
            v = m[2] if m[1] or m[2] else None
            target_attrs[k] = v

    def matches(elem: ET.Element) -> bool:
        if tag_name and elem.tag != tag_name:
            return False
        if element_id and elem.get("id") != element_id:
            return False
        if target_classes:
            elem_classes = (elem.get("class") or "").split()
            if not all(cls in elem_classes for cls in target_classes):
                return False
        if target_attrs:
            if not all((k in elem.attrib) if v is None else elem.get(k) == v for k, v in target_attrs.items()):
                return False
        return True

    if matches(root):
        return root, None
    for parent in root.iter():
        for child in parent:
            if matches(child):
                return child, parent
    return None, None


def find_by_id(root: ET.Element, node_id: str | None) -> ET.Element | None:
    if not node_id:
        return None
    if root.get("id") == node_id:
        return root
    return root.find(f".//*[@id='{node_id}']")


def find_with_parent_by_id(root: ET.Element, node_id: str | None) -> tuple[ET.Element | None, ET.Element | None]:
    # Returns (element, parent) or (None, None)
    if not node_id:
        return None, None
    for parent in root.iter():
        for child in parent:
            if child.get("id") == node_id:
                return child, parent
    # root itself
    if root.get("id") == node_id:
        return root, None
    return None, None


def ensure_unique_include(root: ET.Element, container_tag: str, src_value: str) -> None:
    container = root.find(container_tag)
    if container is None:
        container = ET.Element(container_tag)
        # put styles/scripts at the top for readability
        root.insert(0, container)
    # de-duplicate
    for inc in container.findall("include"):
        if inc.get("src") == src_value:
            return  # already present
    include = ET.SubElement(container, "include")
    include.set("src", src_value)


def apply_modifications(xml_file: str, modifications: list[dict[str, Any]]) -> None:
    if not os.path.exists(xml_file):
        log.write_warning(f"[Missing XML] '{xml_file}' not found; skipping modifications")
        return
    try:
        tree = dET.parse(xml_file)
        root = tree.getroot()
        assert root is not None, "parsed XML has no root element"
    except Exception:
        log.write_warning(f"[XML ParseError] Could not parse {xml_file}")
        return

    for mod in modifications:
        action = mod.get("action")

        if action == "add_script":
            src = mod.get("src", "")
            ensure_unique_include(root, "scripts", src)

        elif action == "add_style_include":
            src = mod.get("src", "")
            ensure_unique_include(root, "styles", src)

        elif action == "set_attribute":
            selector = mod.get("selector")
            element = find_by_selector(root, selector)

            if element is not None:
                attr = mod.get("attribute")
                val = mod.get("value")
                if attr is not None and val is not None:
                    element.set(attr, val)

        elif action == "add_child":
            selector = mod.get("selector")
            parent_elem = find_by_selector(root, selector)
            xml_snippet = mod.get("xml", "")
            if parent_elem is not None and xml_snippet:
                try:
                    child = dET.fromstring(xml_snippet)
                    parent_elem.append(child)
                except ET.ParseError:
                    log.write_warning("[XML ParseError] add_child")
            elif parent_elem is None:
                log.write_warning(f"[add_child] target '{selector}' not found in {os.path.basename(xml_file)}")

        elif action == "move_into":
            selector = mod.get("selector")
            new_parent_selector = mod.get("new_parent_selector")

            elem, old_parent = find_with_parent_by_selector(root, selector)
            new_parent = find_by_selector(root, new_parent_selector)

            if elem is not None and new_parent is not None:
                if old_parent is not None:
                    old_parent.remove(elem)
                new_parent.append(elem)
            else:
                if elem is None:
                    log.write_warning(f"[move_into] target '{selector}' not found in {os.path.basename(xml_file)}")
                if new_parent is None:
                    log.write_warning(
                        f"[move_into] new_parent '{new_parent_selector}' not found in {os.path.basename(xml_file)}"
                    )

        elif action == "insert_after":
            selector = mod.get("selector")
            xml_snippet = mod.get("xml", "")

            target, parent = find_with_parent_by_selector(root, selector)

            if target is not None and parent is not None and xml_snippet:
                try:
                    new_elem = ET.fromstring(xml_snippet)
                    idx = list(parent).index(target)
                    parent.insert(idx + 1, new_elem)
                except ET.ParseError:
                    log.write_warning("[XML ParseError] insert_after")
            elif target is None:
                log.write_warning(f"[insert_after] target '{selector}' not found in {os.path.basename(xml_file)}")
            elif parent is None:
                log.write_warning(
                    f"[insert_after] target '{selector}' has no parent (is root?) in {os.path.basename(xml_file)}"
                )

        elif action == "insert_before":
            selector = mod.get("selector")
            xml_snippet = mod.get("xml", "")

            target, parent = find_with_parent_by_selector(root, selector)

            if target is not None and parent is not None and xml_snippet:
                try:
                    new_elem = ET.fromstring(xml_snippet)
                    idx = list(parent).index(target)
                    parent.insert(idx, new_elem)
                except ET.ParseError:
                    log.write_warning("[XML ParseError] insert_before")
            elif target is None:
                log.write_warning(f"[insert_before] target '{selector}' not found in {os.path.basename(xml_file)}")
            elif parent is None:
                log.write_warning(
                    f"[insert_before] target '{selector}' has no parent (is root?) in {os.path.basename(xml_file)}"
                )

    if hasattr(ET, "indent"):
        ET.indent(tree, space="\t", level=0)

    try:
        tree.write(xml_file, encoding="utf-8", xml_declaration=False)
    except TypeError:
        tree.write(xml_file)


def get_xml_mod_file(mod_path: str) -> str | None:
    xml_json = os.path.join(mod_path, "xml.json")
    return xml_json if os.path.exists(xml_json) else None
