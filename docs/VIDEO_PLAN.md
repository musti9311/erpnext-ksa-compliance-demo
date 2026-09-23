# Video plan — one evening, phone-over-monitor is fine
# Narration script: docs/VIDEO_SCRIPT.md (5 scenes, ~3 min). This is the shoot plan.

## Checklist (do once, 10 min)
- [ ] Screenshots captured first (docs/SCREENSHOTS.md) — doubles as thumbnail source
- [ ] Browser 125% zoom, notifications/Discord closed, phone on silent
- [ ] One test recording (10 sec) — check audio levels before the real takes
- [ ] Mock running (:8090), stack up, logged in as Administrator
- [ ] Water nearby; mistakes are fine — one take per scene, stitch later

## Shot list (maps to VIDEO_SCRIPT scenes)
0. Setup (15s): dashboard at localhost:8080, say who/where/what.
1. QR (30s): print ACC-SINV-2026-00001, zoom QR, read the 5 TLV fields + "+03:00" line.
2. Clearance (35s): click Submit → Cleared + UUID; open the ...00008 invoice → Failed,
   button stays (retry visible). Say "simulated Fatoora, endpoint-switchable".
3. Payroll (30s): Saudi slip (9.75% deduction) vs expat slip (zero) → GL entry for the
   employer half → "HRMS never posted it, so my script does."
4. Controls (50s, do NOT rush): 36k PO without quote → Final Approve → red block message;
   USD 90k PO → still blocked; Supplier timeline → bank-change note. Say the 4-bypass story
   in two sentences: "my tests passed, then I attacked it, found 4 holes, fixed them."
5. Close (20s): repo README on screen, link in comments.

## After upload (YouTube unlisted-first, then LinkedIn same night)
- Chapters: 0:00 Setup / 0:15 QR / 0:45 Clearance / 1:20 Payroll / 1:50 Controls / 2:40 Close
- Subtitles: auto-generate, fix numbers + Arabic terms only (don't hand-translate all)
- Thumbnail: QR screenshot + "29/29 controls" text
- Replace the README "video coming" line with the link (and keep one screenshot anyway —
  many recruiters never press play)
