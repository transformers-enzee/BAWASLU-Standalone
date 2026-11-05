"""Question-first multilingual reply policy for BAWASLU assistant.

No user preferences, UI language, evidence language, or previous answer may
silently override the language of the *latest* user question.
This is a best-effort language hint; the model handles ambiguous Latin text.
"""
import re
import unicodedata

LANGUAGE_NAMES={
    "id":"Bahasa Indonesia","en":"English","es":"Español","fr":"Français",
    "pt":"Português","de":"Deutsch","it":"Italiano","nl":"Nederlands",
    "tr":"Türkçe","vi":"Tiếng Việt","ms":"Bahasa Melayu",
    "ar":"العربية","ru":"Русский","zh":"中文","ja":"日本語",
    "ko":"한국어","th":"ไทย","hi":"हिन्दी","auto":"the language of the latest question",
}
LANG_WORDS={
    "id":set("tolong dibuatkan buatkan dibuat mengenai terhadap dengan untuk dan yang bagaimana apakah jelaskan jelasin sebutkan saya kami dari dalam pada tentang provinsi dugaan pelanggaran pemilih pemilu bawaslu isu terkait ini itu analisis kenapa menurut periksa siapa kapan mana tidak bisa laporan sentimen".split()),
    "en":set("please could would you me my what why when where which who how is are does the this that for with about from into around of analyze analyse analysis detect identify candidate candidates province provincial suspected violation issues electoral election report provide show explain review audience".split()),
    "es":set("por favor que qué como cómo cuales cuáles sobre desde para con una unos las los del el la hay quiero necesito dame muestra explica analiza candidatos provincias violaciones elecciones".split()),
    "fr":set("bonjour pourquoi comment quels quelles quelles pour avec dans est sont des une sur concernant analyse analyser expliquer candidats élections élections preuves".split()),
    "pt":set("por favor como quais com para sobre uma dos das candidatos eleições evidências analisar análise explique mostre".split()),
    "de":set("bitte was warum wie welche über mit und für eine der die das ist sind zeige analysiere kandidaten wahlen".split()),
    "it":set("per favore come cosa perché quali con delle della una il la degli analizza mostra candidati elezioni".split()),
    "nl":set("wat hoe waarom welke over met voor een van het zijn analyseer kandidaten verkiezingen".split()),
    "tr":set("lütfen nasıl hangi neden hakkında ile için bir aday seçimler analiz göster".split()),
    "vi":set("xin hãy cho tôi bạn những của các về trong không phân tích bầu cử tỉnh".split()),
    "ms":set("sila boleh kepada daripada untuk mengenai apakah bagaimanakah calon pilihan raya mengundi negeri".split()),
}
EXPLICIT={
    "bahasa indonesia":"id","indonesian":"id","bahasa inggris":"en","english":"en",
    "español":"es","spanish":"es","français":"fr","french":"fr",
    "português":"pt","portuguese":"pt","deutsch":"de","german":"de",
    "italiano":"it","italian":"it","nederlands":"nl","dutch":"nl",
    "türkçe":"tr","turkish":"tr","tiếng việt":"vi","vietnamese":"vi",
    "bahasa melayu":"ms","malay":"ms","العربية":"ar","arabic":"ar",
    "русский":"ru","russian":"ru","中文":"zh","chinese":"zh",
    "日本語":"ja","japanese":"ja","한국어":"ko","korean":"ko",
    "ไทย":"th","thai":"th","हिन्दी":"hi","hindi":"hi",
}
SCRIPT_PATTERNS=(
    ("ja",r"[\u3040-\u30ff]"),("ko",r"[\uac00-\ud7af]"),
    ("th",r"[\u0e00-\u0e7f]"),("ar",r"[\u0600-\u06ff]"),
    ("hi",r"[\u0900-\u097f]"),("ru",r"[\u0400-\u052f]"),
    ("zh",r"[\u3400-\u9fff]"),
)

def detect_question_language(question):
    """Return BCP-47 primary language subtag or 'auto' for ambiguous text."""
    value=str(question or "").strip()
    if not value:
        return "auto"
    folded=value.casefold()
    # Explicit instructions are stronger than incidental language mentions.
    for phrase,language in EXPLICIT.items():
        if re.search(r"(?:reply|respond|answer|write|jawab|gunakan bahasa|réponds|responde|contesta|répondez|sprich|回答|رد)"
                     r".{0,40}?\b"+re.escape(phrase)+r"\b", folded):
            return language
    for code,pattern in SCRIPT_PATTERNS:
        if re.search(pattern,value):
            return code
    tokens=re.findall(r"[^\W\d_]+", folded,flags=re.UNICODE)
    if not tokens:
        return "auto"
    scores={lang:sum((2 if word in {"tolong","dibuatkan","terhadap","bagaimana","please","what","which","analyze","analyse","pourquoi","bonjour","warum","bitte","por","favor"} else 1)
                     for word in tokens if word in vocab)
            for lang,vocab in LANG_WORDS.items()}
    top=sorted(scores.items(),key=lambda pair:pair[1],reverse=True)
    if not top or not top[0][1]:
        return "auto"
    if top[0][1]==top[1][1]:
        return "auto"
    return top[0][0]

def effective_language(question,reported):
    """The model may resolve ambiguous questions; it cannot override clear ones."""
    explicit=detect_question_language(question)
    if explicit!="auto":
        return explicit
    code=str(reported or "").strip().lower().split("-")[0]
    return code if code in LANGUAGE_NAMES and code!="auto" else "en"

def language_directive(question):
    code=detect_question_language(question)
    target=LANGUAGE_NAMES[code]
    return {
        "hint":code,"language_name":target,
        "rule":(
            "Respond entirely in "+target+". All prose, headings, analytical "
            "observations, uncertainty, suggested actions, tag explanations, and "
            "presentation labels must use this language. Do not copy the language "
            "of source documents or earlier answers. Preserve source IDs, official "
            "names, quotations and legal titles unchanged when required. "
            "Never mix English/Indonesian explanatory headings into another language. "
            "For ambiguous multilingual questions, choose the dominant language of "
            "the *latest user question* and report the ISO language code."
        ),
    }
