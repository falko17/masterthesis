#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import csv
import sys

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x):
        return x


def parse_gxl_to_nodes(file_path):
    print("Parsing GXL file...")
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Find the graph element
    graph = root.find("{http://www.w3.org/1999/xlink}graph") or root.find("graph")

    if graph is None:
        raise ValueError("No graph element found in the GXL file")

    print("Extracting nodes...")
    nodes = []
    for node in tqdm(graph.findall("node")):
        node_data = {"id": node.get("id")}

        # We only care about classes.
        if any(
            t.get("{http://www.w3.org/1999/xlink}href") != "Class"
            for t in node.findall("type")
        ):
            continue

        for attr in node.findall("attr"):
            name = attr.get("name")
            value_elem = attr.find("*")
            if value_elem is not None and name is not None:
                node_data[name] = value_elem.text

        nodes.append(node_data)

    return nodes


def write_csv(nodes, output_file):
    print("Writing CSV...")
    if not nodes:
        print("No nodes found to write to CSV.")
        return

    fieldnames = set()
    for node in nodes:
        fieldnames.update(node.keys())

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
        writer.writeheader()
        for node in nodes:
            writer.writerow(node)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.gxl> <output.csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    nodes = parse_gxl_to_nodes(input_file)
    write_csv(nodes, output_file)
    print(f"Successfully converted {input_file} to {output_file}.")


if __name__ == "__main__":
    main()
