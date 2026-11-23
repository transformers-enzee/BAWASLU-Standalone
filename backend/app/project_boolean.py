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


def discover_boolean_plan(expression,max_keywords=5):
    """Conservative candidate retrieval for SocialCrawl Prism.

    Each keyword is an independent provider search (OR). Every returned row
    must still satisfy the original Boolean AST locally. This planner only
    emits retrieval and server-side filters that cannot exclude a true local
    match; it makes NO promises about search-engine recall, cost or ranking.
    """
    tree,_=parse_boolean(expression)

    def alternatives(node):
        kind=node[0]
        if kind=='TERM':
            return [(node[1],)]
        if kind=='NOT':
            return [()]
        left,right=alternatives(node[1]),alternatives(node[2])
        if kind=='OR':
            return [tuple(dict.fromkeys(a+b)) for a in left for b in right]
        return left+right

    possible=[]
    for option in alternatives(tree):
        if option and len(option)<=max_keywords and option not in possible:
            possible.append(option)
    if not possible:
        raise ValueError('No bounded Prism search plan; use fewer independent OR terms (maximum five)')

    # Search terms within a positive AND arm are alternative *sufficient*
    # retrieval paths. Longer terms tend to be more selective, but that is a
    # heuristic, not a measured frequency or a guarantee.
    def rank(option):
        lengths=[len(x) for x in option]
        return (sum(lengths)/len(lengths) - 0.15*(len(option)-1),-len(option))
    keywords=list(max(possible,key=rank))

    def necessities(node):
        kind=node[0]
        if kind=='TERM':
            return {node[1]},set()
        if kind=='NOT':
            # Only a directly negated literal is safe to push down.
            return (set(),{node[1][1]}) if node[1][0]=='TERM' else (set(),set())
        left_plus,left_minus=necessities(node[1])
        right_plus,right_minus=necessities(node[2])
        if kind=='AND':
            return left_plus|right_plus,left_minus|right_minus
        return left_plus&right_plus,left_minus&right_minus

    required,forbidden=necessities(tree)
    # Exactly one mandatory literal can be pushed down into Prism 'contains'.
    # Do not impose OR-group members individually (would create false negatives).
    candidates=sorted((term for term in required if term not in keywords),
                      key=lambda s:(-len(s),s))
    contains=candidates[0] if candidates else ''
    return {
        'keywords':keywords,
        'contains':contains,
        'exclude_terms':sorted(forbidden),
        'search_mode':'BOOLEAN',
        'strategy':'SELECTIVE_POSITIVE_ARM_WITH_EXACT_LOCAL_BOOLEAN_GATE',
        'post_filter_required':True,
        'provider_boolean_native':False,
        'warning':'Provider keywords are separate searches, not native AND/OR/NOT. '
                  'Server-side text filters and local Boolean checks reduce unrelated '
                  'results, but cannot guarantee coverage or nonzero matches.',
    }
