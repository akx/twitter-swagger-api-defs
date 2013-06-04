import re
import urlparse
from lxml.html import HTMLParser
from lxml import etree

url_param_re = re.compile(r":([a-z_]+)", re.I)


def inner_text(el):
    if not el:
        return None
    if isinstance(el, list):
        el = el[0]
    return etree.tostring(el, method="text", encoding="UTF-8").decode("UTF-8").strip().replace("\n", " ")


def parse_tree(tree):
    title = inner_text(tree.cssselect("#title"))
    is_post = title.startswith("POST")
    endpoint = inner_text(tree.cssselect(".field-doc-resource-url div")).replace("format", "{format}")
    description = inner_text(tree.cssselect(".doc-updated+div>p"))
    url_params = set()

    def fix_url_param(m):
        var = m.group(1)
        url_params.add(var)
        return "{%s}" % var

    endpoint = url_param_re.sub(fix_url_param, endpoint)
    parameters = []
    for param in tree.cssselect("div.parameter"):
        p_name_raw = inner_text(param.cssselect(".param"))
        try:
            p_name, required = p_name_raw.rsplit(" ", 1)
        except ValueError:
            p_name = p_name_raw
            required = "required"
        p_desc = inner_text(param.cssselect("p"))
        parameters.append({
            "name": p_name,
            "description": p_desc,
            "required": (required == "required"),
            "dataType": "string", # Can't assume anything else,
            "paramType": ("path" if p_name in url_params else ("form" if is_post else "query")),
        })

    return {
        "path": urlparse.urlparse(endpoint).path,
        "description": "",
        "operations": [{
            "httpMethod": "POST" if is_post else "GET",
            "nickname": title.lower().replace("/", "_").replace(" ", "_"),
            "responseClass": "complex",
            "parameters": parameters,
            "summary": description,
        }]
    }


def parse_file(fn):
    parser = HTMLParser()
    tree = etree.parse(fn, parser=parser).getroot()
    return parse_tree(tree)


def parse_from_string(s):
    parser = HTMLParser()
    tree = etree.fromstring(s, parser=parser)
    return parse_tree(tree)


def parse_from_zip():
    import zipfile

    apis = []
    zf = zipfile.ZipFile("apidocs.zip")
    for fileinfo in zf.infolist():
        if fileinfo.file_size > 0:
            apis.append(parse_from_string(zf.read(fileinfo)))
    return apis


def main():
    from json import dumps
    apis = parse_from_zip()
    apis.sort(key=lambda api:api["path"])
    print "%d API definitions parsed." % len(apis)
    file("twitter_api.json", "wb").write(dumps(apis, indent=4))


if __name__ == "__main__":
    main()
