"""Officer action guidance; no AI, database, or external network calls."""
import re
_ACTION=re.compile(
 r"apa\s+(?:yang\s+)?(?:harus|perlu)\s+(?:dilakukan|ditindaklanjuti)|"
 r"apa\s+langkah|bagaimana\s+(?:menindaklanjuti|tindak\s+lanjut|penanganan)|"
 r"tindak\s+lanjut|rencana\s+tindakan|rekomendasi\s+(?:aksi|tindakan|bawaslu)|"
 r"what\s+should\s+(?:bawaslu|officers?|the\s+team|we)\s+do|"
 r"next\s+steps?|action\s+plan|recommended\s+actions?|follow.up\s+actions?",re.I)
def officer_action_intent(q):
    return bool(_ACTION.search(str(q or "")))
OFFICER_DECISION_CONTRACT = """
BAWASLU INTERNAL DECISION BRIEF: Serve impartial HQ/provincial election
supervisors, not a generic PR audience. For relevant news, allegations and
intelligence, provide 1) VIOLATION TYPE: reported conduct, tentative legal
domain and allegation vs investigation vs court-confirmed status;
2) GEOGRAPHICAL IMPACT: directly affected province/city only when supported,
never from publication address, government-office location, or monitoring
campaign geography; otherwise state not established;
3) RECOMMENDATION: why it matters for electoral supervision, what electoral
nexus and BAWASLU jurisdiction is or is not demonstrated;
4) PRIORITIZED NEXT ACTIONS: next_checks should contain 3-4 specific distinct
steps, each stating suggested REVIEWING ROLE, evidence to obtain, EXPECTED
OUTPUT and conditional ESCALATION or closure criterion. Begin with source
verification, then assess electoral nexus and law, then decide authorized
routing, referral review, monitoring or reasoned closure.
EVIDENCE HIERARCHY: authorized Inbox and social/news records describe what
was reported; independently verified decisions establish official case status.
PDF passages are supporting page-cited legal/SOP REFERENCES, not the sole
brain or proof that an alleged event occurred. Use professional analysis,
consider alternative explanations and show uncertainty. Cite only authorized
IDs for source-dependent claims. Never invent a violation, criminal guilt,
legal article, province, court ruling, deadline, formal case, officer
assignment, or referral. All decisions require authorized officer review.
If evidence is sparse, explain the gap AND give concrete conditional tasks,
not a repetitive no-evidence disclaimer.
Place immediate decision in direct_answer; observations are source-backed
signals; next_checks are actionable officer review tasks.
"""
_FALLBACK={
"id":[
"Tim intelijen Bawaslu: verifikasi sumber asli, tanggal dan bukti pendukung atau bantahan; keluaran: catatan verifikasi dengan ID sumber.",
"Petugas hukum/kewenangan: telaah hubungan konkret dengan Pemilu/Pilkada dan dasar hukum berlaku; keluaran: kajian kewenangan, bukan penetapan pelanggaran.",
"Koordinator pengawasan: konfirmasi lokasi kejadian sebelum penugasan provinsi; dengan persetujuan, pilih pendalaman, pemantauan, rujukan sah atau penutupan beralasan."
],
"en":[
"BAWASLU intelligence team: check original reporting, dates and corroboration; output: a source-linked verification note.",
"Legal/jurisdiction officer: assess electoral nexus and current law; output: a written jurisdiction recommendation, not a verdict.",
"Oversight supervisor: verify incident location before provincial routing; with approval decide inquiry, limited monitoring, lawful referral review or reasoned closure."
]
}
def complete_officer_steps(question, profile, steps, language="id"):
    current=[x.strip() for x in (steps or []) if isinstance(x,str) and x.strip()]
    if profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT") or not officer_action_intent(question) or len(current)>=3:
        return current,False
    return (current+_FALLBACK.get(language,_FALLBACK["en"])[len(current):])[:4],True
