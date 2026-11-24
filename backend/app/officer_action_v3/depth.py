"""Bounded adaptive research planning; no private evidence in search queries."""
import re

DIMENSIONS=(
 ("national statistics",r"top\s*\d+|rank|statistics|statistik|peringkat|violations|pelanggaran",
  "official national statistics datasets Pemilu Pilkada Bawaslu Renstra LKjIP Satu Data"),
 ("provincial breakdown",r"provinc|provinsi|regional|wilayah|kabupaten",
  "official provincial breakdown table rekapitulasi provinsi Bawaslu LKjIP Satu Data"),
 ("candidate cases",r"candidate|kandidat|calon|paslon",
  "official final decisions candidate cases putusan MK DKPP Bawaslu KPU distinguish allegations"),
 ("party accountability",r"part(?:y|ies)|partai",
  "official KPU party sponsorship and documented legal liability putusan party case evidence"),
 ("subjects and institutions",r"subject|actor|subjek|pelaku|authority|kewenangan",
  "official actor classifications ASN election officials campaign teams competent authorities"),
 ("legal instruments",r"law|legal|regulation|reform|hukum|pasal|peraturan|undang",
  "official controlling laws current amendments JDIH Bawaslu KPU BPK MK provisions effective dates"),
 ("prevention and implementation",r"tackle|effective|strateg|prevent|recommend|roadmap|reform|pencegahan|efektif|strategi",
  "official oversight evaluation enforcement gaps prevention recommendations Bawaslu DPR"),
)
def objectives(question):
    return [(label,hint) for label,pattern,hint in DIMENSIONS if re.search(pattern,question,re.I)]

def depth_for(question):
    q=question.casefold()
    if len(objectives(q))>=3 or re.search(r"\b(deep research|comprehensive|mendalam|komprehensif)\b",q):
        return "DEEP"
    if len(q)<110 and re.search(r"^(what is|define|apa itu|jelaskan arti)\b",q) and not re.search(r"latest|current|terbaru|terkini",q):
        return "QUICK"
    return "STANDARD"

def research_tasks(question,recent=False):
    dims=objectives(question)
    if depth_for(question)=="DEEP":
        # Group related dimensions to control cost while maintaining coverage.
        groups=[dims[i:i+2] for i in range(0,len(dims),2)]
        if not groups:groups=[[("broad research","authoritative sources and comparative evidence")]]
        return [(" / ".join(x[0] for x in group),"; ".join(x[1] for x in group)) for group in groups][:4]
    return [("direct research","official and original reporting; latest corrections where relevant")]

def output_budget(question):
    return {"QUICK":2200,"STANDARD":6000,"DEEP":14000}[depth_for(question)]
