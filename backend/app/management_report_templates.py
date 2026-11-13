"""Built-in BAWASLU INTERIM management report templates.

These are unsigned, read-only management drafts. They use exclusively
permission-scoped casework snapshots supplied by management_reporting;
no secondary database read, paid AI call, legal ruling or approval is made.
"""
from collections import Counter
from html import escape
from io import BytesIO
from urllib.parse import urlsplit

TEMPLATE_VERSION = "INTERIM-1.0"
TEMPLATE_ID = "BAWASLU-OPERATIONS-MANAGEMENT-BRIEF"
LANGUAGES = {"id", "en"}


def _t(language, indonesian, english):
    return indonesian if language == "id" else english


def _clean(value, limit=500):
    return " ".join(str(value or "").split())[:limit]


def _safe_link(raw):
    url = _clean(raw, 1200)
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    return url if parsed.scheme == "https" and parsed.netloc and not parsed.username else ""


def build_interim_template(snapshot, language="id"):
    if language not in LANGUAGES:
        raise ValueError("Unsupported report language")
    metrics = snapshot["metrics"]
    rows = snapshot.get("recent_cases") or []
    period = snapshot["period"]
    topic = snapshot.get("topic_filter") or ""
    scope = snapshot.get("scope") or {}
    place = (_t(language, "Nasional", "National")
             if scope.get("geographic_scope") == "Nationwide"
             else _clean(scope.get("province"), 100) or _t(language, "Wilayah terbatas", "Restricted area"))
    label = {"daily": ("Harian", "Daily"), "weekly": ("Mingguan", "Weekly"),
             "monthly": ("Bulanan", "Monthly")}[period]
    interval = label[0] if language == "id" else label[1]
    title = (_t(language, "Laporan Pemantauan Isu", "Issue Monitoring Brief")
             if topic else _t(language, "Laporan Manajemen Intelijen Pengawasan",
                             "Oversight Intelligence Management Brief"))
    assigned, active, closed = (int(metrics.get(k) or 0) for k in
                                ("assignments", "active_assignments", "closed_assignments"))
    submitted = int(metrics.get("submitted_reports") or 0)
    approved = int(metrics.get("approved_reports") or 0)
    linked = int(metrics.get("unique_linked_sources") or 0)
    summary = (
        f"Selama periode {interval.lower()} dalam cakupan {place}, terdapat {assigned} penugasan petugas "
        f"yang tercatat dari {linked} sumber terkait yang unik. Sebanyak {active} penugasan masih aktif "
        f"dan {closed} ditutup. Terdapat {submitted} laporan berstatus diajukan dan {approved} laporan "
        f"berstatus disetujui dalam alur kerja. Angka ini tidak mengukur seluruh percakapan media sosial "
        f"dan bukan penetapan pelanggaran hukum."
        if language == "id" else
        f"In this {interval.lower()} reporting window for {place}, {assigned} officer assignments "
        f"were created from {linked} distinct linked sources. {active} assignments remain active "
        f"and {closed} were closed. {submitted} related case reports are submitted and {approved} "
        f"have approved workflow status. These are not total social conversation counts "
        f"or confirmed legal violations."
    )
    monitoring = snapshot.get("monitoring") or {}
    monitoring_enabled = monitoring.get("enabled") is True
    if monitoring_enabled:
        observed = int(monitoring.get("published_in_period") or 0)
        unknown = int(monitoring.get("publication_date_unknown") or 0)
        summary += _t(language,
            f" Secara terpisah, {observed} unggahan relevan dalam sampel Inbox berizin memiliki tanggal publikasi dalam periode ini; {unknown} unggahan tidak memiliki cap waktu zona yang dapat dipercaya. Ini bukan jumlah seluruh unggahan yang dikumpulkan.",
            f" Separately, {observed} relevant saved Inbox posts have explicit publication timestamps in the selected window; {unknown} posts lack a reliable zoned timestamp. This is not the total number of captured posts.")
    if monitoring_enabled:
        quality=monitoring.get("source_quality") or {}
        if int(quality.get("missing_original_text") or 0) or int(quality.get("missing_safe_original_url") or 0):
            summary += _t(language,
                f" Sebelum tindak lanjut, periksa {int(quality.get('missing_original_text') or 0)} sumber sampel tanpa teks asli dan {int(quality.get('missing_safe_original_url') or 0)} sumber tanpa tautan asli yang aman.",
                f" Before follow-up, inspect {int(quality.get('missing_original_text') or 0)} sampled sources missing original text and {int(quality.get('missing_safe_original_url') or 0)} without safe original URLs.")
    findings = []
    for case in rows[:8]:
        reference = (f"SOCIAL #{case.get('source_id')} / campaign #{case.get('campaign_id')}"
                     if case.get("source_type") == "SOCIAL"
                     else f"{case.get('source_type') or 'SOURCE'} #{case.get('source_id')}")
        findings.append({
            "case_id": case["id"],
            "title": _clean(case.get("title"), 240),
            "department": _clean(case.get("department"), 120),
            "status": _clean(case.get("status"), 50),
            "report_status": _clean(case.get("latest_report_status") or "-", 40),
            "source_reference": reference,
            "source_url": _safe_link(case.get("source_url")),
            "source_excerpt": _clean(case.get("evidence_excerpt") or case.get("source_excerpt"), 320),
            "verified_province": _clean(case.get("verified_province"), 100),
            "verification_note": _t(language,
                "Status alur kerja; isi sumber belum merupakan temuan hukum yang dipastikan.",
                "Casework status only; source claims are not established legal findings."),
        })
    progress=snapshot.get("casework_progress") or {}
    if progress.get("schema")=="BAWASLU_CASEWORK_PROGRESS_V1534":
        pending=int(progress.get("waiting_for_receiving_team_status") or 0)
        checked=int(progress.get("source_check_attested_in_window") or 0)
        not_observed=int(progress.get("source_review_event_not_observed_in_window") or 0)
        awaiting=int(progress.get("latest_report_awaiting_approval") or 0)
        summary += _t(language,
            f" Dalam casework yang berizin, {checked} penugasan memiliki pemeriksaan sumber asli yang tercatat pada periode ini, sedangkan {not_observed} tidak memiliki catatan pemeriksaan sumber dalam periode. Tidak tercatat bukan berarti belum pernah diperiksa.",
            f" Within authorized casework, {checked} assignments have an audited original-source check in this reporting window; {not_observed} have no source-review event observed in the window. Absence is not proof that no earlier review occurred.")
    pilot=snapshot.get("officer_pilot_readiness") or {}
    pilot_enabled=pilot.get("schema")=="BAWASLU_OFFICER_PILOT_EVIDENCE_V1540"
    if pilot_enabled:
        selected_count=int(pilot.get("authorized_case_count") or 0)
        complete=int(pilot.get("five_stage_observed_case_count") or 0)
        if selected_count:
            summary+=_t(language,
                f" Bukti persiapan uji petugas: {complete} dari {selected_count} penugasan berizin memiliki kelima tahap alur kerja tercatat dalam periode ini. Ini belum merupakan penerimaan resmi; petugas dan pemeriksa harus memberikan persetujuan terpisah.",
                f" Officer-pilot evidence: {complete} of {selected_count} authorized cases have all five workflow stages recorded in this period. This is not formal acceptance; authorized officers and reviewers must sign off separately.")
        else:
            summary+=_t(language,
                " Tidak ada penugasan petugas riil dalam cakupan periode ini untuk evaluasi penerimaan. Keberhasilan uji otomatis tidak membuktikan penerimaan resmi.",
                " No real officer casework is available in this reporting scope for acceptance evaluation. Automated test success does not constitute formal officer acceptance.")
    readiness=snapshot.get("investigation_readiness") or {}
    readiness_enabled=readiness.get("schema")=="BAWASLU_INVESTIGATION_READINESS_V1537"
    if readiness_enabled:
        counts=readiness.get("group_counts") or {}
        need_evidence=int(counts.get("EVIDENCE_RECHECK") or 0)
        historical=int(counts.get("REVIEW_HISTORY_CHECK") or 0)
        officer=int(counts.get("OFFICER_ACTION") or 0)
        pending_independent_count=int(counts.get("INDEPENDENT_REVIEW") or 0)
        summary+=_t(language,
            f" Kesiapan tindak lanjut dalam penugasan berizin: {need_evidence} perlu pemeriksaan sumber ulang, {historical} perlu pemeriksaan riwayat audit, {officer} menunggu tindakan petugas, dan {pending_independent_count} laporan telah diajukan dengan catatan pemeriksaan sumber pada periode ini dan menunggu pemeriksa independen. Kelompok ini tidak memvalidasi fakta atau hukum.",
            f" Investigation follow-up across authorized assignments: {need_evidence} need source rechecks, {historical} need historical audit inspection, {officer} await officer action, and {pending_independent_count} submitted reports have a source-check event recorded in this window and await independent review. These groups do not validate facts or law.")
    followup=snapshot.get("followup_queue") or {}
    followup_enabled=followup.get("schema")=="BAWASLU_AUTHORIZED_FOLLOWUP_QUEUE_V1536"
    if followup_enabled:
        total=int(followup.get("attention_count") or 0)
        urgent=int((followup.get("priority_counts") or {}).get("P1") or 0)
        summary += _t(language,
            f" Dalam penugasan yang dibuat pada periode laporan ini, {total} kasus memiliki petunjuk tindak lanjut operasional, termasuk {urgent} prioritas P1. P1 menunjukkan urutan tinjauan, bukan tingkat pelanggaran.",
            f" Among assignments created in this reporting window, {total} have suggested operational follow-up, including {urgent} P1 review items. P1 is review order, not violation severity.")
    followup_labels={"RECEIVING_TEAM_ACCEPTANCE":["Konfirmasi penerimaan oleh tim petugas","Confirm receiving-team acceptance"],"CASE_INFORMATION_FOLLOWUP":["Lengkapi informasi kasus yang masih dibutuhkan","Complete missing case information"],"SOURCE_REVIEW_RECHECK":["Periksa ulang catatan sumber dan bukti asli","Recheck original-source review record"],"CHECK_HISTORICAL_SOURCE_REVIEW":["Periksa riwayat audit untuk verifikasi sumber sebelumnya","Inspect audit history for earlier source review"],"SUBMIT_OR_REVISE_LATEST_REPORT":["Lengkapi atau ajukan ulang versi laporan terbaru","Complete or resubmit latest report version"],"CREATE_OFFICER_REPORT":["Susun laporan petugas berdasarkan sumber yang ditinjau","Prepare officer report based on reviewed source"],"INDEPENDENT_REPORT_REVIEW":["Minta telaah independen atas laporan yang diajukan","Request independent review of submitted report"],"RECONCILE_CASE_REPORT_STATUS":["Selaraskan status kasus dan persetujuan laporan yang tidak konsisten","Reconcile conflicting case and report approval states"]}
    actions = []
    if pilot_enabled:
        if not pilot.get("real_casework_available_in_scope"):
            actions.append(_t(language,
                "Sebelum persetujuan formal, pilih kasus riil yang sah dan berizin untuk dievaluasi oleh petugas penerima dan pemeriksa independen.",
                "Before formal acceptance, select an authorized real case for receiving-officer and independent-reviewer evaluation."))
        elif int(pilot.get("five_stage_observed_case_count") or 0)<int(pilot.get("authorized_case_count") or 0):
            actions.append(_t(language,
                "Tinjau langkah audit yang belum tercatat pada kasus berizin, kemudian minta penerimaan manusia yang terpisah. Catatan pada periode sebelumnya mungkin tetap berlaku.",
                "Review absent audit stages in authorized cases, then obtain separate human acceptance. Earlier-period audit records may exist."))
    if readiness_enabled:
        counts=readiness.get("group_counts") or {}
        if int(counts.get("EVIDENCE_RECHECK") or 0):
            actions.append(_t(language,
                f"Periksa ulang sumber asli pada {int(counts.get('EVIDENCE_RECHECK') or 0)} kasus dengan catatan pemeriksaan terakhir dalam periode ini yang belum memenuhi syarat pemeriksaan; jangan menarik kesimpulan hukum.",
                f"Recheck original sources for {int(counts.get('EVIDENCE_RECHECK') or 0)} cases whose latest observed review did not satisfy source-check attestation. Do not infer legal outcomes."))
        if int(counts.get("REVIEW_HISTORY_CHECK") or 0):
            actions.append(_t(language,
                f"Telaah riwayat audit pada {int(counts.get('REVIEW_HISTORY_CHECK') or 0)} kasus tanpa catatan pemeriksaan sumber yang terlihat dalam periode ini. Catatan lebih lama mungkin tersedia.",
                f"Inspect historical audit records for {int(counts.get('REVIEW_HISTORY_CHECK') or 0)} cases without a source-review event observed in this period; earlier records may exist."))
    if followup_enabled:
        for item in (followup.get("items") or [])[:3]:
            case_id=int(item.get("case_id") or 0)
            labels=followup_labels.get(item.get("action_code"))
            if case_id>0 and labels:
                priority=item.get("priority") if item.get("priority") in ("P1","P2","P3") else "P3"
                actions.append(_t(language,
                    f"Kasus #{case_id} ({priority}): {labels[0]}. Periksa izin dan bukti pada alur kerja Inbox sebelum bertindak.",
                    f"Case #{case_id} ({priority}): {labels[1]}. Recheck permissions and evidence in the Inbox workflow before any action."))
    if progress.get("schema")=="BAWASLU_CASEWORK_PROGRESS_V1534":
        if pending:
            actions.append(_t(language,
                f"Tindaklanjuti penerimaan penugasan untuk {pending} kasus berstatus baru atau ditugaskan; pastikan otorisasi petugas penerima.",
                f"Follow up receiving-officer acceptance for {pending} cases currently open or assigned; confirm authorized ownership."))
        needs=int(progress.get("source_review_requires_attention_in_window") or 0)
        if needs:
            actions.append(_t(language,
                f"Tinjau kembali {needs} catatan pemeriksaan sumber yang belum memenuhi syarat verifikasi sumber asli dalam periode ini.",
                f"Recheck {needs} source-review records that do not meet original-source attestation conditions in this window."))
        if awaiting:
            actions.append(_t(language,
                f"Sebelum merujuk {awaiting} laporan terbaru yang diajukan ke pemeriksa independen berwenang, periksa riwayat sumber asli dan status kasus. Pengajuan tidak membuktikan kelengkapan verifikasi.",
                f"Before routing {awaiting} latest submitted reports to authorized independent reviewers, check source-review history and case status. Submission alone does not prove verification."))

    if active:
        actions.append(_t(language,
            f"Tinjau {active} penugasan aktif terhadap sumber asli dan bukti pendukung; catat verifikasi petugas.",
            f"Review {active} active assignments against original sources and supporting evidence; record officer verification."))
    if submitted:
        actions.append(_t(language,
            f"Serahkan {submitted} laporan yang diajukan kepada pemeriksa berwenang yang independen.",
            f"Route {submitted} submitted case reports to an independent authorized reviewer."))
    unknown_province = sum(1 for row in rows if not row.get("verified_province"))
    if unknown_province:
        actions.append(_t(language,
            f"Konfirmasi kewenangan dan lokasi kejadian untuk {unknown_province} penugasan yang ditampilkan tanpa provinsi kejadian terverifikasi.",
            f"Confirm jurisdiction and incident location for {unknown_province} displayed assignments lacking a verified incident province."))
    if not assigned:
        actions.append(_t(language,
            "Tidak ada penugasan tersimpan dalam cakupan dan periode ini; periksa cakupan pengumpulan dan antrian Inbox sebelum menyimpulkan tidak ada isu.",
            "No saved assignments in this scope and window. Check collection coverage and the Inbox before inferring that no issues exist."))
    if not actions:
        actions.append(_t(language,
            "Lakukan pemantauan lanjutan dan pemeriksaan sumber asli sebelum keputusan penanganan.",
            "Continue monitoring and verify original evidence before any follow-up decision."))
    if monitoring_enabled and int(monitoring.get("flagged_potential_violation_posts") or 0):
        actions.append(_t(language,
            "Prioritaskan pemeriksaan sumber asli pada unggahan Inbox bertanda dugaan pelanggaran; jangan anggap sinyal otomatis sebagai kesimpulan hukum.",
            "Prioritize original-source verification for flagged Inbox posts; an automated signal is not a legal finding."))
    if monitoring_enabled:
        quality=monitoring.get("source_quality") or {}
        for row in (quality.get("review_priorities") or [])[:5]:
            count=int(row.get("affected_sources") or 0)
            code=row.get("code")
            if code=="VERIFY_ORIGINAL_POST_TEXT":
                actions.append(_t(language,
                    f"Periksa teks unggahan asli untuk {count} sumber yang terpantau sebelum membuat rekomendasi.",
                    f"Verify original post text for {count} monitored sources before recommending follow-up."))
            elif code=="VERIFY_ORIGINAL_SOURCE_URL":
                actions.append(_t(language,
                    f"Verifikasi tautan asli untuk {count} sumber; tautan yang aman belum berarti konten telah diperiksa.",
                    f"Validate original links for {count} sources; a safe URL does not verify the content."))
            elif code=="RECONCILE_CONFLICTING_SAVED_EXCERPTS":
                actions.append(_t(language,
                    f"Cocokkan kutipan berbeda pada {count} sumber tersimpan dengan postingan aslinya.",
                    f"Reconcile conflicting saved excerpts for {count} sources against the original posts."))
            elif code=="CHECK_CURRENT_PLATFORM_RULES":
                actions.append(_t(language,
                    f"Cari dan telaah aturan resmi platform untuk {count} sumber dengan referensi aturan yang belum tersedia.",
                    f"Locate current official platform policies for {count} sources without configured rules."))
            elif code=="RECOVER_EXPLICIT_PUBLICATION_TIME":
                actions.append(_t(language,
                    f"Konfirmasi waktu publikasi asli untuk {count} sumber tanpa tanggal andal sebelum menilai periode.",
                    f"Confirm original publication times for {count} sources lacking reliable timestamps before assigning them to the reporting period."))
    coverage = snapshot.get("report_coverage") or {}
    case_count = int(metrics.get("assignments") or 0)
    sampled = len(findings)
    coverage_note = _t(language,
        f"Penugasan dalam periode: {case_count}. Rincian kasus dalam draf: {sampled} dari maksimal 8. "
        f"Laporan berdasarkan versi terbaru per penugasan: {int(metrics.get('assignments_with_reports') or 0)} "
        f"penugasan memiliki laporan, {int(metrics.get('assignments_without_reports') or 0)} belum memiliki laporan.",
        f"Assignments in reporting period: {case_count}. Detailed cases included: {sampled}, maximum 8. "
        f"Using only the latest report version per assignment, {int(metrics.get('assignments_with_reports') or 0)} "
        f"assignments have reports and {int(metrics.get('assignments_without_reports') or 0)} have none.")
    if followup_enabled:
        # Follow-up text is a read-only management aid. Records outside the
        # reporting cohort and earlier review events are not established absent.
        pass
    if pilot_enabled:
        caveats_note=_t(language,
            "Kesiapan uji petugas dihitung dari peristiwa audit yang tercatat dalam periode UTC terpilih; bukan riwayat seumur hidup, bukan bukti keaslian sumber, dan bukan persetujuan klien.",
            "Officer-pilot readiness reflects audit events observed in the selected UTC window; it is not lifetime casework history, evidence-authenticity proof, or client approval.")
    caveats = [
        coverage_note,
        *([caveats_note] if pilot_enabled else []),
        _t(language,
           "Status laporan yang dihitung berasal dari versi laporan terbaru pada setiap penugasan; versi lama tetap dalam jejak audit tetapi tidak menggandakan KPI.",
           "Report-status KPIs use the latest report version per assignment; older versions remain in the audit trail but do not inflate KPIs."),
        _t(language,
           "Hanya penugasan casework yang dapat diakses oleh pengguna ini, dibuat dalam periode UTC bergulir yang dipilih. Bukan sensus seluruh posting atau Inbox.",
           "Only casework assignments authorized for this user and created in the selected rolling UTC window. Not a census of all posts or Inbox items."),
        _t(language,
           "Daftar temuan dan lampiran sumber menampilkan maksimal 8 penugasan terbaru. KPI mencakup seluruh penugasan yang memenuhi kriteria.",
           "Finding details and source appendix show at most eight recent assignments. KPIs use all matching assignments."),
        _t(language,
           "Status penugasan dan laporan merupakan status operasional, bukan bukti kesalahan, verifikasi legal, atau keputusan penghapusan konten.",
           "Assignment and report states are operational statuses, not proof of guilt, statutory validation, or a content-removal decision."),
        _t(language,
           "Template sementara ini bukan format resmi BAWASLU; membutuhkan pemeriksaan dan persetujuan petugas sebelum distribusi.",
           "This interim template is not an official BAWASLU format; it requires officer review and approval before distribution."),
    ]
    if monitoring_enabled:
        caveats.extend([
            _t(language,
                "Bagian pemantauan diambil dari sampel Inbox relevan berizin yang dibatasi 300 tautan per kampanye. Sumber dihitung unik lintas kampanye, bukan seluruh pengumpulan atau seluruh percakapan.",
                "Monitoring draws from a bounded authorized, relevant Inbox window of up to 300 links per campaign. Sources are unique across campaigns, not all captured content or online conversations."),
            _t(language,
                f"Periode pemantauan dihitung dari waktu publikasi asli yang memiliki zona waktu: {int(monitoring.get('published_in_period') or 0)} tercakup, {int(monitoring.get('publication_date_unknown') or 0)} tanpa waktu yang dapat dipastikan, {int(monitoring.get('published_outside_period') or 0)} di luar periode. Kelengkapan sampel tidak dapat dipastikan.",
                f"Monitoring uses only original publication timestamps with explicit offsets: {int(monitoring.get('published_in_period') or 0)} in period, {int(monitoring.get('publication_date_unknown') or 0)} without reliable timestamps, {int(monitoring.get('published_outside_period') or 0)} outside the period. Sample completeness is unknown."),
            _t(language,
                "Angka monitoring dan penugasan dipisahkan karena berasal dari populasi dan waktu dasar berbeda; tidak ada dugaan yang dikonfirmasi sebagai pelanggaran.",
                "Monitoring and assignment KPIs use different populations and time bases. No suspected issue is a confirmed legal violation."),
            _t(language,
                f"Kategori indikasi dapat tumpang tindih: {int(monitoring.get('signal_overlapping_sources_in_period') or 0)} unggahan memiliki lebih dari satu indikasi dan jumlah kategori tidak boleh dijumlahkan. Konflik waktu publikasi {int(monitoring.get('source_publication_time_conflicts') or 0)}, sentimen {int(monitoring.get('source_sentiment_conflicts') or 0)}, dan platform {int(monitoring.get('source_platform_conflicts') or 0)} ditandai, bukan ditebak.",
                f"Signal categories are non-additive: {int(monitoring.get('signal_overlapping_sources_in_period') or 0)} posts have overlapping preliminary signals. Duplicate finding links are deduplicated. Conflicting publication times ({int(monitoring.get('source_publication_time_conflicts') or 0)}), sentiments ({int(monitoring.get('source_sentiment_conflicts') or 0)}), and platforms ({int(monitoring.get('source_platform_conflicts') or 0)}) are flagged, not guessed."),
        ])
    if readiness_enabled:
        caveats.append(_t(language,
            "Klasifikasi kesiapan investigasi adalah petunjuk alur kerja. Catatan sumber hanya diperiksa dalam periode pelaporan yang dipilih. Laporan diajukan tidak sama dengan fakta, dasar hukum, atau persetujuan akhir yang telah diverifikasi.",
            "Investigation readiness is workflow triage. Source events are observed only in the selected reporting period. A submitted report is not proof of verified facts, applicable law, or final approval."))
    if followup_enabled:
        caveats.append(_t(language,
            "Daftar tindak lanjut menunjukkan maksimal 12 kasus dalam cakupan yang dibuat pada periode ini. Kasus lama tidak ikut dalam populasi; catatan sumber yang tidak terlihat dalam periode bisa ada pada riwayat sebelumnya. Petunjuk tidak melakukan penugasan atau persetujuan otomatis.",
            "Follow-up preview shows at most 12 authorized cases created in this period. Older cases are outside the cohort and earlier source-review events may exist. Suggestions do not assign, approve, or close cases."))
    scorecard = [
        {"label": _t(language,"Penugasan","Assignments"), "value":assigned},
        {"label": _t(language,"Sumber unik","Unique sources"),"value":linked},
        {"label": _t(language,"Masih aktif","Active cases"),"value":active},
        {"label": _t(language,"Laporan disetujui","Reports approved"),"value":approved},
    ]
    if monitoring_enabled:
        scorecard.extend([
            {"label": _t(language,"Unggahan terpantau (sampel)","Observed Inbox posts (sample)"),
             "value":int(monitoring.get("published_in_period") or 0)},
            {"label": _t(language,"Unggahan bertanda dugaan","Flagged source posts"),
             "value":int(monitoring.get("flagged_potential_violation_posts") or 0)},
        ])
    return {
        "template_id": TEMPLATE_ID,
        "template_version": TEMPLATE_VERSION,
        "approval_state": "DRAFT_NOT_APPROVED",
        "language": language,
        "title": title,
        "subtitle": _t(language, "DRAF INTERNAL · TEMPLATE SEMENTARA",
                        "INTERNAL DRAFT · INTERIM TEMPLATE"),
        "period_label": interval,
        "topic": topic,
        "scope_label": place,
        "window_start_utc": snapshot["window_start_utc"],
        "window_end_utc": snapshot["window_end_utc"],
        "executive_summary": summary,
        "scorecard": scorecard,
        "monitoring_summary": monitoring if monitoring_enabled else {"enabled":False},
        "operational_breakdown": [
            {"label":_clean(key,120),"value":int(value)}
            for key,value in sorted(snapshot.get("department_counts",{}).items(),
                                    key=lambda x:(-x[1],x[0]))],
        "findings": findings,
        "recommended_actions": actions,
        "officer_pilot_evidence":({
            "schema":"BAWASLU_OFFICER_PILOT_EVIDENCE_V1540",
            "authorized_case_count":int(pilot.get("authorized_case_count") or 0),
            "five_stage_observed_case_count":int(pilot.get("five_stage_observed_case_count") or 0),
            "automated_pilot_acceptance_granted":False,
            "authorized_human_signoff_received":False,
            "window_only_not_lifetime_casework":True,
        } if pilot_enabled else None),
        "investigation_readiness_summary":({
            "schema":"BAWASLU_INVESTIGATION_READINESS_V1537",
            "authorized_case_count":int(readiness.get("authorized_case_count") or 0),
            "review_attention_count":int(readiness.get("review_attention_count") or 0),
            "group_counts":{key:int(value) for key,value in (readiness.get("group_counts") or {}).items()
                            if key in ("EVIDENCE_RECHECK","REVIEW_HISTORY_CHECK","OFFICER_ACTION",
                                       "INDEPENDENT_REVIEW","WORKFLOW_COMPLETE","OTHER_FOLLOWUP")},
            "historical_review_uncertain":True,
            "source_truth_verified":False,
            "legal_outcome_confirmed":False,
            "automatic_actions_created":False,
        } if readiness_enabled else None),
        "followup_queue_summary":({
            "schema":"BAWASLU_AUTHORIZED_FOLLOWUP_QUEUE_V1536",
            "attention_count":int(followup.get("attention_count") or 0),
            "priority_counts":followup.get("priority_counts") or {},
            "preview_is_sample":bool(followup.get("preview_is_sample")),
            "only_authorized_cases":True,
            "automatic_actions_created":False,
        } if followup_enabled else None),
        "methodology": caveats,
        "coverage_note": coverage_note,
        "report_status_basis": "LATEST_REPORT_PER_AUTHORIZED_ASSIGNMENT",
        "source_appendix": [
            {"case_id":row["case_id"],"source_reference":row["source_reference"],
             "source_url":row["source_url"],"status":row["status"]}
            for row in findings],
        "signoff": {
            "prepared_by":"","reviewed_by":"","approved_by":"","date":"",
        },
        "paid_provider_called": False,
        "automated_legal_verdict": False,
    }


def render_docx(template):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

    language=template["language"]
    t=lambda id,en: _t(language,id,en)
    document=Document()
    section=document.sections[0]
    section.top_margin=Cm(2.2)
    section.bottom_margin=Cm(2.1)
    section.left_margin=section.right_margin=Cm(2.25)
    styles=document.styles
    normal=styles["Normal"]
    normal.font.name="Aptos"
    normal.font.size=Pt(9.3)
    normal.font.color.rgb=RGBColor(38,53,68)
    normal.paragraph_format.space_after=Pt(7)
    for name,size in (("Title",21),("Heading 1",13),("Heading 2",10.5)):
        style=styles[name]
        style.font.name="Aptos Display"
        style.font.size=Pt(size)
        style.font.bold=True
        style.font.color.rgb=RGBColor(128,27,36)
        style.paragraph_format.space_before=Pt(12)
        style.paragraph_format.space_after=Pt(6)
    header=section.header.paragraphs[0]
    header.text="BAWASLU  |  "+template["subtitle"]
    header.style="Caption"
    footer=section.footer.paragraphs[0]
    footer.text="BAWASLU · "+template["template_version"]+" · "+t("DRAF BELUM DISETUJUI","UNAPPROVED DRAFT")
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    footer.style="Caption"
    document.add_heading(template["title"],0)
    document.add_paragraph(template["subtitle"])
    info=document.add_table(rows=0, cols=2)
    info.alignment=WD_TABLE_ALIGNMENT.CENTER
    info.style="Light Shading Accent 1"
    for label,value in [
        (t("Periode","Reporting period"),template["period_label"]),
        (t("Jendela UTC","UTC window"),template["window_start_utc"]+"  —  "+template["window_end_utc"]),
        (t("Cakupan wilayah","Geographic scope"),template["scope_label"]),
        (t("Topik","Topic"),template["topic"] or t("Semua penugasan yang diizinkan","All authorized assignments")),
        (t("Status dokumen","Document status"),template["approval_state"]),
    ]:
        cells=info.add_row().cells
        cells[0].text=label
        cells[1].text=str(value)
        for cell in cells:
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    document.add_heading(t("01  Ringkasan Eksekutif","01  Executive Summary"),1)
    document.add_paragraph(template["executive_summary"])
    document.add_heading(t("02  Indikator Utama","02  Key Indicators"),1)
    table=document.add_table(rows=1,cols=2)
    table.style="Light Shading Accent 1"
    table.rows[0].cells[0].text=t("Indikator","Indicator")
    table.rows[0].cells[1].text=t("Jumlah","Count")
    for item in template["scorecard"]:
        a,b=table.add_row().cells
        a.text=item["label"]
        b.text=str(item["value"])
    document.add_heading(t("03  Temuan Terhubung Sumber","03  Source-Linked Casework"),1)
    if template["findings"]:
        for i,item in enumerate(template["findings"],1):
            document.add_heading(str(i)+". "+item["title"],2)
            document.add_paragraph(
                t("Penugasan","Assignment")+" #"+str(item["case_id"])+" | "+
                item["department"]+" | "+item["status"]+" | "+
                item["source_reference"])
            if item["source_excerpt"]:
                document.add_paragraph(t("Kutipan sumber: ","Source excerpt: ")+item["source_excerpt"])
            document.add_paragraph(item["verification_note"])
    else:
        document.add_paragraph(t("Tidak ada penugasan yang sesuai periode dan akses.","No assignments match this period and access scope."))
    document.add_heading(t("04  Rekomendasi Tindak Lanjut","04  Recommended Next Checks"),1)
    for action in template["recommended_actions"]:
        document.add_paragraph(action,style="List Bullet")
    document.add_heading(t("05  Ringkasan Beban Kerja Unit","05  Department Workload"),1)
    if template["operational_breakdown"]:
        for row in template["operational_breakdown"]:
            document.add_paragraph(row["label"]+": "+str(row["value"]),style="List Bullet")
    else:
        document.add_paragraph(t("Tidak ada penugasan yang tercatat.","No recorded assignments."))
    document.add_heading(t("06  Lampiran Sumber","06  Evidence Reference Appendix"),1)
    if template["source_appendix"]:
        for item in template["source_appendix"]:
            document.add_paragraph(
                "Case #"+str(item["case_id"])+" · "+item["source_reference"]+
                " · "+item["status"]+(" · "+item["source_url"] if item["source_url"] else ""),
                style="List Bullet")
    else:
        document.add_paragraph(t("Tidak ada rujukan.","No source references."))
    document.add_heading(t("07  Dasar Data dan Batasan","07  Data Basis and Limitations"),1)
    for caveat in template["methodology"]:
        document.add_paragraph(caveat,style="List Bullet")
    document.add_heading(t("08  Pemeriksaan & Persetujuan","08  Review and Sign-Off"),1)
    for role in [
        t("Disusun oleh","Prepared by"),
        t("Ditelaah oleh","Reviewed by"),
        t("Disetujui oleh","Approved by"),
        t("Tanggal","Date"),
    ]:
        document.add_paragraph(role+": ______________________________")
    buffer=BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_pdf(template):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.units import mm

    lang=template["language"]
    t=lambda id,en: _t(lang,id,en)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BAWTitle",fontName="Helvetica-Bold",
        fontSize=18,leading=22,textColor=colors.HexColor("#801B24"),spaceAfter=8))
    styles.add(ParagraphStyle(name="BAWSection",fontName="Helvetica-Bold",
        fontSize=11.5,leading=15,textColor=colors.HexColor("#801B24"),
        spaceBefore=13,spaceAfter=6,keepWithNext=True))
    styles.add(ParagraphStyle(name="BAWBody",fontName="Helvetica",
        fontSize=9,leading=13,textColor=colors.HexColor("#283C4D"),spaceAfter=6))
    styles.add(ParagraphStyle(name="BAWMuted",parent=styles["BAWBody"],
        fontSize=8,textColor=colors.HexColor("#657586")))
    styles.add(ParagraphStyle(name="BAWTag",parent=styles["BAWBody"],
        textColor=colors.HexColor("#801B24"),fontName="Helvetica-Bold"))
    para=lambda txt,style="BAWBody",limit=3000:Paragraph(escape(_clean(txt,limit)),styles[style])
    doc_buffer=BytesIO()
    document=SimpleDocTemplate(doc_buffer,pagesize=A4,
        leftMargin=20*mm,rightMargin=20*mm,topMargin=22*mm,bottomMargin=20*mm,
        title=template["title"],author="BAWASLU Interim Reporting")
    story=[
        para(template["subtitle"],"BAWTag"),
        para(template["title"],"BAWTitle"),
        para(template["period_label"]+" | "+template["scope_label"],"BAWMuted"),
        para(template["window_start_utc"]+"  -  "+template["window_end_utc"],"BAWMuted"),
        para(t("Topik: ","Topic: ")+(template["topic"] or t("Semua penugasan","All assignments")),"BAWMuted"),
        para(t("01  Ringkasan Eksekutif","01  Executive Summary"),"BAWSection"),
        para(template["executive_summary"],limit=6000)
    ]
    score=[[_clean(t("Indikator","Indicator")),_clean(t("Jumlah","Count"))]]
    score += [[x["label"],str(x["value"])] for x in template["scorecard"]]
    score_table=Table([[para(value) for value in row] for row in score],colWidths=[122*mm,46*mm],hAlign="LEFT",repeatRows=1)
    score_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#F1E8E9")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LINEBELOW",(0,0),(-1,0),0.5,colors.HexColor("#801B24")),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,1),(-1,-1),0.2,colors.HexColor("#E1E6EC")),
    ]))
    story += [para(t("02  Indikator Utama","02  Key Indicators"),"BAWSection"),score_table]
    story.append(para(t("03  Penugasan dengan Rujukan","03  Source-Linked Assignments"),"BAWSection"))
    if template["findings"]:
        for i,item in enumerate(template["findings"],1):
            block=[
                para(str(i)+". "+item["title"],"BAWTag"),
                para("#"+str(item["case_id"])+" | "+item["department"]+" | "+item["status"]+" | "+item["source_reference"],"BAWMuted"),
            ]
            if item["source_excerpt"]:
                block.append(para(t("Kutipan sumber: ","Source excerpt: ")+item["source_excerpt"]))
            block.append(para(item["verification_note"],"BAWMuted"))
            story.append(KeepTogether(block))
    else:
        story.append(para(t("Tidak ada penugasan yang sesuai.","No matching assignments.")))
    story.append(para(t("04  Rekomendasi Tindak Lanjut","04  Recommended Next Checks"),"BAWSection"))
    for i,action in enumerate(template["recommended_actions"],1):
        story.append(para(str(i)+". "+action))
    story.append(para(t("05  Beban Kerja Unit","05  Department Workload"),"BAWSection"))
    for row in template["operational_breakdown"]:
        story.append(para(row["label"]+" - "+str(row["value"])))
    if not template["operational_breakdown"]:
        story.append(para(t("Tidak ada penugasan.","No assignments.")))
    story.append(para(t("06  Lampiran Rujukan","06  Evidence Appendix"),"BAWSection"))
    for row in template["source_appendix"]:
        story.append(para("#"+str(row["case_id"])+" | "+row["source_reference"]+" | "+row["status"]))
        if row["source_url"]:
            story.append(para(row["source_url"],"BAWMuted"))
    if not template["source_appendix"]:
        story.append(para(t("Tidak ada rujukan.","No references.")))
    story.append(para(t("07  Dasar Data & Batasan","07  Basis & Limitations"),"BAWSection"))
    for caveat in template["methodology"]:
        story.append(para("- "+caveat,"BAWMuted"))
    story.append(para(t("08  Pemeriksaan & Persetujuan","08  Review & Sign-Off"),"BAWSection"))
    for role in [
        t("Disusun oleh","Prepared by"),
        t("Ditelaah oleh","Reviewed by"),
        t("Disetujui oleh","Approved by"),
        t("Tanggal","Date"),
    ]:
        story.append(para(role+": _________________________"))

    def page_footer(canvas,doc):
        canvas.saveState()
        canvas.setFont("Helvetica",7.2)
        canvas.setFillColor(colors.HexColor("#728094"))
        canvas.drawString(20*mm,11*mm,"BAWASLU · "+TEMPLATE_VERSION+" · "+
            t("DRAF BELUM DISETUJUI","UNAPPROVED DRAFT"))
        canvas.drawRightString(190*mm,11*mm,str(doc.page))
        canvas.restoreState()
    document.build(story,onFirstPage=page_footer,onLaterPages=page_footer)
    return doc_buffer.getvalue()


def render_xlsx(template):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb=Workbook()
    summary=wb.active
    summary.title="Report Summary"
    detail=wb.create_sheet("Source Appendix")
    lang=template["language"]
    t=lambda id,en: _t(lang,id,en)

    def safe(value):
        value=str(value if value is not None else "")
        if value.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'"+value
        return value

    for row in [
        [template["title"]],
        [template["subtitle"]],
        [t("Status","Status"),template["approval_state"]],
        [t("Periode","Period"),template["period_label"]],
        [t("Mulai UTC","Start UTC"),template["window_start_utc"]],
        [t("Akhir UTC","End UTC"),template["window_end_utc"]],
        [t("Cakupan","Scope"),template["scope_label"]],
        [t("Topik","Topic"),template["topic"]],
        [],
        [t("Ringkasan Eksekutif","Executive Summary")],
        [template["executive_summary"]],
        [],
        [t("Indikator","Indicator"),t("Jumlah","Value")],
    ]:
        summary.append([safe(value) for value in row])
    for item in template["scorecard"]:
        summary.append([safe(item["label"]),item["value"]])
    summary.append([])
    summary.append([t("Tindak Lanjut yang Direkomendasikan","Recommended Next Checks")])
    for step in template["recommended_actions"]:
        summary.append([safe(step)])
    summary.append([])
    summary.append([t("Batasan","Limitations")])
    for caveat in template["methodology"]:
        summary.append([safe(caveat)])
    summary.append([])
    for role in [
        t("Disusun oleh","Prepared by"),t("Ditelaah oleh","Reviewed by"),
        t("Disetujui oleh","Approved by"),t("Tanggal","Date"),
    ]:
        summary.append([role,""])
    detail.append(["Case ID","Source ID","Case title","Case status","Department",
                   "Verified province","Source excerpt","Source URL"])
    for item in template["findings"]:
        detail.append([
            item["case_id"],safe(item["source_reference"]),safe(item["title"]),
            safe(item["status"]),safe(item["department"]),safe(item["verified_province"]),
            safe(item["source_excerpt"]),safe(item["source_url"])
        ])
    for sheet in (summary,detail):
        sheet.freeze_panes="A2"
        sheet.sheet_view.showGridLines=False
        for cell in sheet[1]:
            cell.font=Font(bold=True,color="FFFFFF")
            cell.fill=PatternFill("solid",fgColor="801B24")
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment=Alignment(vertical="top",wrap_text=True)
        sheet.column_dimensions["A"].width=55
        sheet.column_dimensions["B"].width=44
    for col,width in {"C":45,"D":18,"E":30,"F":24,"G":50,"H":50}.items():
        detail.column_dimensions[col].width=width
    for row in detail.iter_rows(min_row=2):
        for cell in row:
            cell.alignment=Alignment(vertical="top",wrap_text=True)
    output=BytesIO()
    wb.save(output)
    return output.getvalue()
