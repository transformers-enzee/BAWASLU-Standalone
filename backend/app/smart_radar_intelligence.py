"""Phase 3 conservative, source-grounded topic grouping.

This pilot grouping is NOT a legal conclusion or a substitute for saved AI
assessment. Topic groups represent discussion themes unless explicitly marked
as an identifiable reported case. Never imply independent corroboration from
multiple reposts.
"""
import re
import hashlib
from collections import Counter, defaultdict

# Stable IDs avoid duplicate officer actions across dashboard perspectives.
THEMES = {
 "gibran_eligibility":{
  "title":"Gibran eligibility dispute and election-supervision responses",
  "kind":"narrative",
  "players":["narratives","concerns"],
  "perspectives":["operations","reputation"],
  "topics":["Disputes / Legal","Candidates and Political Actors","Election Operations"],
  "review":True,
  "operations":"Coverage focuses on proceedings concerning Gibran's education eligibility, the applicable electoral procedures and differing institutional/legal positions. BAWASLU officers may need to monitor case developments; the underlying allegations are disputed.",
  "reputation":"Public discussion is scrutinizing what BAWASLU and KPU checked and communicated about candidate eligibility. Verify the exact institutional statements and timeline before responding; posts do not establish an oversight failure."
 },
 "dkpp_national":{
  "title":"DKPP complaints involving national election commissioners",
  "kind":"case",
  "players":["concerns","narratives"],
  "perspectives":["operations","reputation"],
  "topics":["Potential Violations","Electoral Institutions","Public Concerns"],
  "review":True,
  "operations":"Sources report ethics complaints concerning national KPU/BAWASLU officials in connection with candidate-selection procedures. Confirm the individual complaints and their procedural status; a complaint is not an ethics ruling.",
  "reputation":"The reported DKPP complaints may affect public confidence in BAWASLU's impartiality and procedures. Officers should distinguish filed complaints from established findings and verify any official response."
 },
 "dkpp_langkat":{
  "title":"Reported DKPP examination of a Langkat election official",
  "kind":"case",
  "players":["concerns"],
  "perspectives":["operations"],
  "topics":["Potential Violations","Electoral Institutions"],
  "review":True,
  "operations":"A source describes a DKPP ethics examination involving the KPU in Langkat. Check the specific proceedings and supporting evidence before deciding whether BAWASLU follow-up is required.",
  "reputation":"This is principally an election-organizer ethics matter, not automatically a complaint about BAWASLU."
 },
 "allowance_discussion":{
  "title":"Public discussion of BAWASLU performance allowances",
  "kind":"narrative",
  "players":["narratives","concerns"],
  "perspectives":["reputation","operations"],
  "topics":["Public Concerns","Electoral Institutions"],
  "review":False,
  "operations":"Posts discuss the timing of BAWASLU staff allowance changes around an earlier election period. Treat claims about motivations as unverified; confirm the documented policy and timing.",
  "reputation":"Commentary about BAWASLU staff allowances could shape public perceptions of institutional independence. A factual policy explanation may be useful if public concern persists; no improper motive is established by these posts."
 },
 "voter_register":{
  "title":"Ongoing voter-list updating and PDPB oversight",
  "kind":"theme",
  "players":["narratives"],
  "perspectives":["operations"],
  "topics":["Voter Register / PDPB","Election Operations"],
  "review":False,
  "operations":"Several sources discuss voter-list maintenance and BAWASLU oversight of continuing updates. These are chiefly administrative reports; no specific irregularity should be inferred without supporting evidence.",
  "reputation":"Public information about voter-list oversight can support understanding of BAWASLU's mandate."
 },
 "party_identity":{
  "title":"Concerns about political-party use of citizens' identities",
  "kind":"theme",
  "players":["concerns"],
  "perspectives":["operations","reputation"],
  "topics":["Public Concerns","Election Operations"],
  "review":False,
  "operations":"Discussion highlights precautions against citizens' identities being used for party membership without permission. The available posts may describe warnings rather than documented individual incidents.",
  "reputation":"Clear guidance on how citizens can report suspected misuse of their identities could reinforce confidence in election oversight."
 },
 "public_participation":{
  "title":"Community participation and election-supervision education",
  "kind":"theme",
  "players":["narratives"],
  "perspectives":["operations","reputation"],
  "topics":["Civic Participation","Election Operations"],
  "review":False,
  "operations":"Posts describe civic education, participatory monitoring and collaboration with community institutions. These are activity updates, not in themselves evidence of electoral violations.",
  "reputation":"Publicized outreach and education activities describe how BAWASLU engages communities. They are evidence of communications activity, not a measured improvement in public trust."
 },
 "service_communication":{
  "title":"BAWASLU services, complaint-handling and public communication",
  "kind":"theme",
  "players":["concerns","narratives"],
  "perspectives":["reputation","operations"],
  "topics":["Public Concerns","Election Operations"],
  "review":False,
  "operations":"Sources describe complaint-handling guidance, staff training and service procedures. These updates should be distinguished from actual filed complaints.",
  "reputation":"Public-facing service announcements and complaint-handling information may influence perceptions of BAWASLU's accessibility. Verify service performance separately rather than inferring it from announcements."
 },
 "digital_discussion":{
  "title":"Election-information integrity and digital discussion",
  "kind":"narrative",
  "players":["narratives"],
  "perspectives":["operations","reputation"],
  "topics":["Emerging Narratives","Election Operations"],
  "review":False,
  "operations":"Posts discuss election-related information circulating online. Repetition alone does not establish deliberate coordination or misinformation.",
  "reputation":"BAWASLU appears in discussion about responsible digital election information. Any communications response should distinguish documented falsehoods from opinions and unverified allegations."
 },
 "election_reform":{
  "title":"Election procedures, participation and proposed reforms",
  "kind":"theme",
  "players":["narratives"],
  "perspectives":["operations"],
  "topics":["Election Operations","Civic Participation"],
  "review":False,
  "operations":"Posts discuss rules, voting participation, future electoral reforms and institutional procedures. These are primarily subjects for awareness, not automatic investigations.",
  "reputation":"Institutional explanations may be relevant to public understanding of election rules."
 },
 "other_election_updates":{
  "title":"Other election-supervision and institutional updates",
  "kind":"theme",
  "players":["narratives"],
  "perspectives":["operations"],
  "topics":["Election Operations"],
  "review":False,
  "operations":"Remaining pilot sources cover varied election-supervision activities and commentary. This is an information overview, not one shared incident or an allegation requiring a single case decision.",
  "reputation":"The underlying sources should be reviewed individually before inferring public confidence."
 }
}

def assign_theme(post):
    t=str(post.get("message_original") or "").lower()
    # Narrow, evidence-based case identifiers come before general narrative grouping.
    if re.search(r"dkpp|dewan kehormatan",t):
        if re.search(r"langkat",t) and re.search(r"sidang|periksa|perkara|pelanggaran",t):
            return "dkpp_langkat"
        if re.search(r"(themis|yayasan dewi keadilan)",t) and re.search(r"bawaslu",t):
            return "dkpp_national"
    if re.search(r"gibran|ijazah wapres|syarat pendidikan (?:calon|wakil)",t) and re.search(r"ijazah|pendidikan|mk|mahkamah konstitusi|phpu|pencalonan|syarat",t):
        return "gibran_eligibility"
    if re.search(r"tunjangan kinerja|\btukin\b",t) and re.search(r"bawaslu|pengawas pemilu",t):
        return "allowance_discussion"
    if re.search(r"dicatut|pencatutan|tanpa izin",t) and re.search(r"anggota par|identitas warga|partai politik",t):
        return "party_identity"
    if re.search(r"pdpb|pemutakhiran data pemilih|daftar pemilih berkelanjutan|data pemilih|dpt\b",t):
        return "voter_register"
    if re.search(r"maklumat pelayanan|pelayanan laporan|pelayanan sengketa|layanan penyelesaian|penanganan pengaduan|pelatihan pelayanan|uji kecakapan",t):
        return "service_communication"
    if re.search(r"pengawasan partisipatif|pendidikan politik|pendidikan demokrasi|sosialisasi|bimtek|bimbingan teknis|relawan|saksi tps|pengawas tps|partisipasi masyarakat|sinergi.*masyarakat|konsolidasi demokrasi",t):
        return "public_participation"
    if re.search(r"ruang digital|hoaks|misinformasi|disinformasi|literasi digital",t):
        return "digital_discussion"
    if re.search(r"ruu pemilu|panja pemilu|revisi undang|partisipasi pemilih|golput|pemilu 2029",t):
        return "election_reform"
    return "other_election_updates"

def _actor_mentions(post,actors):
    return set(actors(post.get("message_original") or ""))

def build_topic_findings(posts,states,assessments,actors,source_view):
    buckets={}
    for p in posts:
        theme=assign_theme(p)
        descriptor=THEMES[theme]
        # Each original post belongs to exactly one primary theme. Multi-topic
        # and multi-perspective classification does not multiply source counts.
        fid="RADAR-"+theme.upper().replace("_","-")
        if fid not in buckets:
            buckets[fid]=dict(
                id=fid,title=descriptor["title"],theme=theme,kind=descriptor["kind"],
                players=list(descriptor["players"]),perspectives=list(descriptor["perspectives"]),
                topics=set(descriptor["topics"]),insights={
                    "operations":descriptor["operations"],
                    "reputation":descriptor["reputation"]},
                posts=[],platform_counts=Counter(),day_counts=Counter(),actor_mentions=Counter(),
                priority_score=None,priority_label="Not AI-scored",geography="Not verified",
                published_at="",review_suggested=descriptor["review"],assessment_count=0
            )
        b=buckets[fid]
        b["posts"].append(source_view(p))
        b["platform_counts"][(p.get("platform") or "Unknown").title()]+=1
        day=str(p.get("published_at_raw") or "")[:10]
        if day:b["day_counts"][day]+=1
        b["actor_mentions"].update(_actor_mentions(p,actors))
        b["published_at"]=max(b["published_at"],str(p.get("published_at_raw") or ""))
        a=assessments.get(p["pilot_post_id"]) or {}
        result=a.get("result_json") or {}
        if isinstance(result,str):
            import json
            try:result=json.loads(result)
            except ValueError:result={}
        if not isinstance(result,dict):result={}
        if a:
            b["assessment_count"]+=1
            score=a.get("priority_score")
            if isinstance(score,int):
                b["_priority_list"]=b.get("_priority_list",[])+[score]
        # AI-generated topic tags can supplement, not erase the verified
        # description. Unrecognized or string-typed tags never enter taxonomy.
        allowed={"Allegations / Violations","Citizen Reports / Public Concerns","Digital Risks / Information",
                 "Disputes / Legal","Election Operations","Participatory Oversight","Voter Register / PDPB"}
        b["topics"].update(x for x in (result.get("topics") or []) if isinstance(x,str) and x in allowed)
    for fid,b in buckets.items():
        manual=states.get(fid) or {}
        # Small group of strongly evidenced reported disputes are queued for
        # an initial officer *triage*, not marked verified or assigned a risk score.
        # A review decision is always human; a provisional suggestion is not QC.
        b["status"]=manual.get("status") or ("pending" if b["review_suggested"] else "awareness")
        b["human_reviewed"]=bool(manual.get("first_reviewed_at"))
        b["next_followup"]=str(manual["next_followup"]) if manual.get("next_followup") else ""
        b["updated_at"]=str(manual.get("updated_at") or "")
        b["topics"]=sorted(b["topics"])
        b["supporting_posts"]=len(b["posts"])
        scores=b.pop("_priority_list",[])
        if scores:
            b["priority_score"]=max(scores)
            b["priority_label"]="High Priority" if b["priority_score"]>=75 else "Medium Priority" if b["priority_score"]>=50 else "Routine"
        elif b["review_suggested"]:
            b["priority_label"]="Review suggested · Unscored"
        b["summary"]=b["insights"]["operations"]
        b["platform_counts"]=dict(b["platform_counts"])
        b["day_counts"]=dict(b["day_counts"])
        b["actor_mentions"]=dict(b["actor_mentions"])
        b["source_ids"]=[p["pilot_post_id"] for p in b["posts"]]
        b["source_signature"]=hashlib.sha256((
          "\n".join(sorted(p["pilot_post_id"]+":"+str(p.get("message_original") or "") for p in b["posts"]))
        ).encode("utf-8")).hexdigest()
        b["ai_summary"]=False
        b["review_basis"]="Preliminary source-based triage" if b["review_suggested"] else "For Awareness"
        b["last_update"]=b["updated_at"] or b["published_at"]
    return sorted(buckets.values(),
                  key=lambda b:(b["status"]!="pending",-(b["priority_score"] or 0),-b["supporting_posts"],b["title"]))
