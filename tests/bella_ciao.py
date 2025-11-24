import xml.etree.ElementTree as ET

if __name__ == "__main__":

    tree = ET.parse("../Data/score.xml")   # or .xml
    root = tree.getroot()

    print(root.tag, root.attrib)

    for child in root:
        print(child.tag, child.attrib)

    # All parts
    ns = {'mx': 'score-partwise'}  # auto-grab the default ns
    print("Namespace:", ns)
    parts = root.findall('part', ns)
    part = parts[0]
    print(parts[0].attrib)
    


