"""Versioned, schema-compatible Boolean project search configuration.

Existing monitoring_projects data remains in monitoring_campaigns; database
schema, IDs, access checks and existing keyword mode stay unchanged.
The primary_keywords_json field permits either legacy keyword arrays or a
versioned Boolean expression object. No provider or database writes here.
"""
import json
import re

SCHEMA="BAWASLU_PROJECT_BOOLEAN_V1"
MAX_QUERY_LENGTH=512
MAX_TOKENS=64
MAX_DEPTH=12
MAX_TERM_LENGTH=120
_TOKEN=re.compile(r"\s+|[()]|\"(?:\\.|[^\"\\])*\"|[^\s()\"]+")


def _tokens(raw):
    if not isinstance(raw,str) or not raw.strip() or len(raw)>MAX_QUERY_LENGTH:
        raise ValueError("Boolean query must contain 1-512 characters")
    values=[]
    index=0
    while index<len(raw):
        match=_TOKEN.match(raw,index)
        if not match:
            raise ValueError("Invalid quotation mark or Boolean token")
        index=match.end()
        token=match.group()
        if token.isspace():
            continue
        if token.startswith('"'):
            try:
                value=json.loads(token)
            except (ValueError,TypeError):
                raise ValueError("Close quoted phrases; use backslash to escape quotes")
            kind="TERM"
        elif token in ("(",")"):
            kind=token
            value=token
        else:
            kind=token.upper() if token.upper() in ("AND","OR","NOT") else "TERM"
            value=token
        if kind=="TERM" and (not value.strip() or len(value)>MAX_TERM_LENGTH):
            raise ValueError("Each Boolean term must contain 1-120 characters")
        values.append((kind,value))
        if len(values)>MAX_TOKENS:
            raise ValueError("Boolean query exceeds 64 tokens")
    return values


def parse_boolean(expression):
    """Return (AST, minimal positive retrieval anchors).

    A single positive anchor set is sufficient for AND; OR requires union.
    A branch whose truth relies only on NOT has no bounded provider query.
    We reject those queries rather than silently searching an entire feed.
    """
    tokens=_tokens(expression)
    pos=0

    def peek():
        return tokens[pos][0] if pos<len(tokens) else None

    def or_expr(depth):
        nonlocal pos
        node=and_expr(depth)
        while peek()=="OR":
            pos+=1
            node=("OR",node,and_expr(depth))
        return node

    def and_expr(depth):
        nonlocal pos
        node=unary(depth)
        while peek() in ("AND","NOT"):
            if peek()=="AND":
                pos+=1
            node=("AND",node,unary(depth))
        return node

    def unary(depth):
        nonlocal pos
        if depth>MAX_DEPTH:
            raise ValueError("Boolean query has more than 12 nested levels")
        kind=peek()
        if kind=="NOT":
            pos+=1
            return ("NOT",unary(depth+1))
        if kind=="(":
            pos+=1
            node=or_expr(depth+1)
            if peek()!=")":
                raise ValueError("Close the Boolean group with )")
            pos+=1
            return node
        if kind=="TERM":
            value=tokens[pos][1].casefold()
            pos+=1
            return ("TERM",value)
        raise ValueError("Expected a word, quoted phrase, NOT or ( group )")

    tree=or_expr(0)
    if pos!=len(tokens):
        raise ValueError("Add AND or OR between terms; check parentheses")

    def covers(node):
        kind=node[0]
        if kind=="TERM":
            return [node[1]]
        if kind=="NOT":
            return None
        left,right=covers(node[1]),covers(node[2])
        if kind=="OR":
            if left is None or right is None:
                return None
            return list(dict.fromkeys(left+right))
        # For AND, either positive branch is sufficient to retrieve a
        # candidate; choose fewer provider searches to bound credit costs.
        if left is None:
            return right
        if right is None:
            return left
        return left if len(left)<=len(right) else right

    anchors=covers(tree)
    if not anchors:
        raise ValueError("Boolean monitoring requires a positive search term in every OR branch")
    if len(anchors)>30:
        raise ValueError("Boolean query requires too many retrieval terms (maximum 30)")
    return tree,anchors


def evaluate_boolean(tree,text):
    content=str(text or "").casefold()

    def check(node):
        kind=node[0]
        if kind=="TERM":
            return node[1] in content
        if kind=="NOT":
            return not check(node[1])
        if kind=="AND":
            return check(node[1]) and check(node[2])
        return check(node[1]) or check(node[2])

    return check(tree)


def decode_project_query(primary_keywords_json):
    """Read legacy keyword arrays or a versioned Boolean project query."""
    try:
        parsed=json.loads(primary_keywords_json or "[]")
    except (TypeError,ValueError):
        parsed=[]
    if isinstance(parsed,list):
        return {"search_mode":"KEYWORDS","boolean_query":"",
                "retrieval_terms":[str(x) for x in parsed if isinstance(x,str)]}
    if isinstance(parsed,dict) and parsed.get("schema")==SCHEMA:
        expression=parsed.get("expression")
        tree,anchors=parse_boolean(expression)
        return {"search_mode":"BOOLEAN","boolean_query":expression,
                "retrieval_terms":anchors,"ast":tree}
    raise ValueError("Unsupported saved monitoring project search configuration")


def encode_boolean_project_query(expression):
    parse_boolean(expression)
    return json.dumps({"schema":SCHEMA,"expression":expression.strip()},
                      ensure_ascii=False,separators=(",",":"))
