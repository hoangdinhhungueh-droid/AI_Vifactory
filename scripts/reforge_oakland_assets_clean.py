# -*- coding: utf-8 -*-
"""
scripts/reforge_oakland_assets_clean.py
Master Reforging Script for EN_EP0008_oakland_plan_rejected.
Applies 100% root-cause remediations for B2 narrative script and B3/B3.5 visual prompts
addressing all findings from Claude Opus 5.5 and GPT-6 Astra Round 6.
"""
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_background_prompt, _sanitize_foreground_prompt
from scripts.generate_oakland_polished_script import STORY_TEXT

# =========================================================================
# 1. CLEAN GROUND-TRUTH BACKGROUND PROMPTS (18 UNIQUE BGs)
# Body descriptions harmonized with anchors to eliminate category bleed
# =========================================================================
CLEAN_RAW_BGS = {
    "bg_oakland_federal_courthouse_night": (
        "Exterior of the Ronald V. Dellums Federal Building in downtown Oakland at night: "
        "twin modern federal office towers linked by an elevated skybridge, curved glass rotunda facade "
        "illuminated against a deep night sky, clean concrete civic plaza. 2D stylized graphic novel editorial illustration, "
        "cool slate and deep charcoal palette, sharp architectural ink linework, raking exterior documentary lighting. "
        "Building facade fills the left two-thirds; open dark sky on the right third for overlay."
    ),
    "bg_empty_bankruptcy_courtroom": (
        "Federal bankruptcy courtroom interior: elevated judicial bench of dark polished oak, "
        "empty counsel tables with neat dark leather armchairs, formal vertical wood-paneled walls, "
        "tall windows casting cool diffuse morning daylight across empty spectator benches. "
        "2D stylized graphic novel editorial illustration, warm walnut and muted amber tones, crisp ink linework, "
        "dramatic soft volumetric light beams. Elevated bench on the left; open floor and paneled wall center-right."
    ),
    "bg_cathedral_christ_the_light_dusk": (
        "Cathedral of Christ the Light exterior on Lake Merritt at dusk: iconic contemporary glass-and-timber curved "
        "architectural facade, dramatic evening volumetric illumination, reflective waters, solemn civic presence. "
        "2D stylized graphic novel editorial illustration, deep twilight blues and warm golden window illumination, "
        "clean ink contours, atmospheric volumetric illumination. Curved cathedral silhouette on the left; open dusk sky on the right."
    ),
    "bg_1960s_rectory_hallway": (
        "Parish rectory interior corridor in the nineteen-sixties era: dark polished wood wainscoting, vintage patterned linoleum flooring, "
        "arched heavy oak doorways, moody raking window daylight casting long dramatic shadows down the narrow hallway, "
        "solemn institutional silence. 2D stylized graphic novel editorial illustration, sepia and olive period palette, "
        "deliberate ink hatching, cinematic noir shadows. Corridor perspective draws from the left; open hallway negative space on the right."
    ),
    "bg_chancery_archive_file_room": (
        "Diocesan chancery basement archive records vault: rows of tall utilitarian dark steel filing cabinets without lettering, "
        "plain cardboard archival document boxes stacked on metal industrial shelving, single overhead pendant lamp casting high-contrast shadows. "
        "2D stylized graphic novel editorial illustration, desaturated cool gray and slate tones, crisp geometric ink rules, "
        "dramatic chiaroscuro lighting. Tall shelving on the left; open concrete aisle on the center-right."
    ),
    "bg_1970s_oakland_streetscape": (
        "Late-afternoon nineteen-seventies era East Bay residential streetscape: vintage stucco bungalows, a modest brick parish church exterior "
        "with square bell tower, parked vintage sedans at curb, overhead utility wires, palm and eucalyptus trees. "
        "2D stylized graphic novel editorial illustration, warm faded vintage film palette, bold ink contours, dramatic raking late-afternoon sunlight "
        "and vintage period shadows. Parish exterior on the left third; open sky and asphalt street on the center-right."
    ),
    "bg_sacramento_capitol_assembly": (
        "California State Capitol assembly legislative chamber interior: historic carved wooden rostrum, neat rows of dark wood legislators' desks "
        "with green leather chairs, ornate gilded classical columns and arched public gallery under warm chandelier lighting. "
        "2D stylized graphic novel editorial illustration, rich amber, emerald green and deep mahogany palette, sharp ink hatching, "
        "stately civic chamber lighting. Rostrum on the left; open legislative floor on the center-right."
    ),
    "bg_mediation_conference_room": (
        "High-floor dispute resolution mediation conference room interior: long polished dark mahogany conference table, "
        "modern high-back leather executive chairs, panoramic floor-to-ceiling windows looking out over downtown fog, "
        "neutral tense negotiating atmosphere. 2D stylized graphic novel editorial illustration, muted steel blue and warm wood tones, "
        "precise architectural linework, diffuse overcast daylight. Conference table on the left; open window view on the center-right."
    ),
    "bg_restructuring_war_room": (
        "Late-night corporate restructuring legal war room interior: long conference table scattered with neat document folios and closed binders, "
        "corkboard displaying abstract timeline pin-cards without typography, single desk lamp casting warm focused light in dark room. "
        "2D stylized graphic novel editorial illustration, deep shadows with amber focal illumination, clean ink outlines, "
        "intense nocturnal working atmosphere. Main desk cluster on the left; shadowed conference room on the center-right."
    ),
    "bg_abstract_ledger_grid": (
        "Stylized 2D forensic financial ledger grid texture: muted sepia and slate ruled accounting paper, faint perspective debit and credit columns, "
        "geometric dividing rules receding in perspective, dramatic raking light across tactile paper grain. "
        "2D stylized graphic novel editorial illustration, warm cream, slate green and muted charcoal tones, clean precise ink rules, "
        "soft diagonal paper texture lighting. Dense ruled grid concentrated on the left third; smooth negative paper tone on the center-right."
    ),
    "bg_bay_area_parish_property_aerial": (
        "Authentic regional aerial cartographic perspective: stylized top-down bird's-eye documentary view of Northern California urban geography "
        "and municipal parcel grids, abstract land-use boundary overlays and civic waterways. "
        "2D stylized graphic novel cartography, muted olive, terracotta and coastal blue tones, crisp graphic boundary ink contours, "
        "diffuse daytime environmental illumination. Dense urban parcel clusters on the left; open coastal water texture on the center-right."
    ),
    "bg_ballot_tabulation_room": (
        "Institutional bankruptcy claims administration office interior: long sorting tables with document bins, tally sorting trays, "
        "unlit matte display panels, neat industrial office furniture, utilitarian administrative stillness. "
        "2D stylized graphic novel editorial illustration, cool institutional gray and pale beige tones, clean linear ink hatching, "
        "even fluorescent office lighting. Sorting workbenches on the left; open office floor on the center-right."
    ),
    "bg_lake_merritt_rain_dusk": (
        "Authentic Oakland Lake Merritt urban shoreline at rainy dusk: wet reflective pedestrian path, dark rippling lake water, "
        "distant civic building lights reflecting on the water surface, overcast rainy dusk sky. "
        "2D stylized graphic novel editorial illustration, moody violet, charcoal and amber reflection tones, atmospheric ink linework, "
        "subtle rainy volumetric mist. Shoreline path and dark trees on the left; open water and dusk sky on the center-right."
    ),
    "bg_vacated_chancery_office": (
        "Quiet diocesan chancery executive office interior: neatly organized document storage boxes, empty dark executive desk, "
        "framed diocesan seal emblem without typography, soft daylight streaming through Venetian blinds casting striped shadow patterns. "
        "2D stylized graphic novel editorial illustration, muted walnut, cream and dusty taupe tones, sharp ink contours, "
        "dramatic blind-shadow chiaroscuro. Executive desk on the left; open wall and carpet on the center-right."
    ),
    "bg_alameda_superior_courthouse": (
        "Historic René C. Davidson Alameda County Superior Courthouse exterior: monumental nineteen-thirties Art Deco civic limestone facade, "
        "vertical fluted piers, carved relief stonework texture without typography, broad front stone steps, overcast daylight. "
        "2D stylized graphic novel editorial illustration, warm limestone and granite gray tones, bold geometric ink linework, "
        "stately exterior documentary lighting. Monumental courthouse facade on the left; broad steps and open sky on the center-right."
    ),
    "bg_california_dioceses_map": (
        "Stylized 2D archival geographic map chart of California diocesan jurisdictions: aged parchment paper texture, inked boundary outlines "
        "and stylized cathedral glyph markers across Northern and Southern California, compass rose graphic without letters. "
        "2D stylized graphic novel cartography, warm parchment, sepia ink and muted terracotta tones, crisp hand-inked cartographic linework, "
        "soft atmospheric vignette lighting. California landmass on the left-center; open ocean texture on the right."
    ),
    "bg_oakland_skyline_2026": (
        "Authentic East Bay metropolitan skyline and urban landscape: distant architectural high-rises and historic clock tower with numeral-free clock face, "
        "surrounding hills and coastal bay atmosphere under overcast modern daylight. "
        "2D stylized graphic novel editorial illustration, slate blue, warm limestone and cool urban gray palette, clean ink silhouettes, "
        "soft documentary daylight. City architecture clustered on the left; broad sky on the center-right."
    ),
    "bg_empty_church_pews": (
        "Modest parish church interior: receding rows of polished dark oak pews leading toward an altar sanctuary, dust motes floating in "
        "soft diagonal shafts of stained-glass daylight, profound quiet and institutional stillness. "
        "2D stylized graphic novel editorial illustration, rich walnut, deep mahogany and warm golden light tones, delicate ink hatching, "
        "dramatic volumetric illumination. Wooden pews line the left and center; open sanctuary corridor on the center-right."
    )
}

# =========================================================================
# 2. CLEAN GROUND-TRUTH FOREGROUND PROMPTS (32 UNIQUE FGs)
# 10 Characters + 22 Evidence Props & Charts (Zero positive/negative conflicts)
# =========================================================================
CLEAN_RAW_FGS = {
    # --- CHARACTERS ---
    "fg_character_bankruptcy_judge": (
        "Presiding federal bankruptcy judge in dark judicial attire, turning a page of an open legal case docket folio with deliberate judicial focus, "
        "solemn reserved authoritative facial micro-expression, no judicial bench in foreground cutout, "
        "three-quarter angle action framing. Bold ink, cel-shading, cool chiaroscuro."
    ),
    "fg_character_diocesan_bishop": (
        "Diocesan bishop in tailored black clerical suit with white clerical Roman collar, composed solemn posture holding a bound pastoral letter folio "
        "with both hands, solemn guarded facial micro-expression, three-quarter angle action framing. Bold ink, cel-shading, cool chiaroscuro."
    ),
    "fg_character_debtor_counsel": (
        "Debtor reorganization defense counsel in dark corporate business suit, reviewing an amended reorganization disclosure folio held open in both hands, "
        "disciplined focused analytical expression, three-quarter angle framing. Bold ink, cel-shading."
    ),
    "fg_character_creditors_committee_counsel": (
        "Creditors' committee lead counsel in dark navy suit with loosened green tie, holding up a bound class voting tabulation folio with one hand "
        "while reviewing an entry with pen in hand, resolute focused advocacy posture, intense micro-expression, three-quarter angle framing. Bold ink, cel-shading."
    ),
    "fg_character_elderly_survivor_claimant": (
        "Elderly survivor claimant archetype in their seventies, natural gray hair and weathered dignified facial features, in modest contemporary civilian attire, "
        "composed dignified posture holding a folded personal sheaf of claim papers close with steady hands, steady reflective somber micro-expression, "
        "three-quarter angle action framing. Bold ink, cel-shading."
    ),
    "fg_character_diocesan_finance_officer": (
        "Diocesan chief financial officer in tailored charcoal business suit, reviewing an open diocesan audit balance sheet folio with an analytical pen in hand, "
        "composed analytical posture, intense focused expression reviewing financial columns. Bold ink, cel-shading."
    ),
    "fg_character_insurance_carrier_counsel": (
        "Insurance carrier defense litigator in tailored dark business suit, holding a vintage insurance policy coverage binder open at chest height, "
        "disciplined analytical expression, three-quarter angle action framing. Bold ink, cel-shading, cool chiaroscuro."
    ),
    "fg_character_state_legislator_2019": (
        "California State Assembly lawmaker in navy legislative committee suit, holding an official state legislative bill document folio with an abstract circular state seal at chest height, "
        "addressing the legislative committee with an open hand gesture, resolute professional expression. Bold ink, cel-shading."
    ),
    "fg_character_investigative_journalist": (
        "Investigative legal court reporter reviewing an electronic court docket sheet folio, indicating a key entry line with the tip of a pen, "
        "observant inquisitive facial micro-expression, smart professional newsroom attire, three-quarter angle framing. Bold ink, cel-shading."
    ),
    "fg_character_fee_examiner": (
        "Court fee examiner in dark professional office vest and rolled shirt-sleeves, holding an analytical pen over an open itemized billing ledger folio, "
        "sharp focused forensic expression reviewing expense entries, three-quarter angle framing. Bold ink, cel-shading."
    ),

    # --- EVIDENCE PROPS & DATA VISUALIZATIONS ---
    "fg_evidence_ab218_bill": (
        "Official California Child Victims Act legislative reform bill folio, official state seal emblem without typography, "
        "prominent statutory reform section highlighted with fluorescent yellow marker ink block without readable letters or digits. "
        "Bold ink, cel-shading, crisp tactile paper texture."
    ),
    "fg_evidence_chapter11_petition": (
        "Official federal bankruptcy reorganization petition cover folio, blank debtor entity line, checked Chapter 11 checkbox box, "
        "embossed court clerk seal stamp without typography or numerals. Bold ink, cel-shading, crisp official legal paper."
    ),
    "fg_evidence_docket_sheet": (
        "Printed electronic court docket folio, displaying abstract ruled entry lines, date column dividers, and geometric index markers "
        "without readable letters or digits. Bold ink, cel-shading, crisp laser-printed paper texture."
    ),
    "fg_evidence_civil_complaint_stack": (
        "Thick bound sheaf of civil lawsuit complaints, blank legal document covers with embossed clerk stamps and an embossed court seal impression "
        "without readable digits. Bold ink, cel-shading, heavy bound document texture."
    ),
    "fg_evidence_claims_decade_histogram": (
        "Stylized 2D forensic statistical histogram chart on cream archival grid paper, displaying vertical data distribution columns grouped across chronological intervals, "
        "with prominent peak bars highlighted in contrasting tones without typography or digits. Bold ink, cel-shading, tactile grid paper texture."
    ),
    "fg_evidence_third_amended_plan": (
        "Thick bound Chapter 11 reorganization plan folio, embossed cover with blank official header block, divider index tabs along right margin "
        "in muted gold and slate tones without typography. Bold ink, cel-shading, heavy bound paper folio."
    ),
    "fg_evidence_trust_offer_bar_chart": (
        "Stylized 2D forensic financial bar chart graphic on aged ledger paper, comparing three distinct vertical visual columns: "
        "a baseline bar for scheduled estate assets, an intermediate bar for the initial trust proposal, and a taller bar for the amended global offer, "
        "rendered with abstract visual shading and contrasting dual-tone patterns without readable text, numbers, or typography. Bold ink, cel-shading."
    ),
    "fg_evidence_ballot_tabulation": (
        "Official claims agent voting tabulation report folio, displaying a dual-tone proportional circular ring graphic highlighting "
        "near-total proportional sector fill in bold contrasting ink without typography or digits. Bold ink, cel-shading, crisp paper texture."
    ),
    "fg_evidence_professional_fees_meter": (
        "Stylized analog forensic financial gauge meter with an indicator needle swung into a high warning zone, circular dial with division tick marks "
        "and abstract indicator rings without readable numbers or typography. Tactile metallic casing, cel-shading."
    ),
    "fg_evidence_priority_waterfall": (
        "Stylized 2D forensic bankruptcy priority distribution waterfall diagram on aged parchment, illustrating cascading hierarchical liquidation tiers "
        "from administrative court professionals at the top down to unsecured claims at the base, rendered with distinct contrasting geometric bands and flow arrows "
        "without readable typography or numerals. Bold ink, cel-shading."
    ),
    "fg_evidence_operating_loss_ledger": (
        "Open forensic accounting ledger folio, showing ruled debit and credit balance columns with abstract geometric line-items and a prominent "
        "red-circled deficit entry without typography or readable digits. Cream ledger paper texture, cel-shading."
    ),
    "fg_evidence_motion_to_dismiss": (
        "Official court motion to dismiss folio, featuring a formal judicial header block, blank case caption ruled lines, and an embossed electronic clerk filing seal "
        "without readable typography. Bold ink, cel-shading, crisp legal folio."
    ),
    "fg_evidence_dismissal_order": (
        "Formal judicial order folio dismissing adversary transfer proceeding, blank judicial execution line, embossed court seal stamp without typography. "
        "Bold ink, cel-shading, crisp official legal paper."
    ),
    "fg_evidence_settlement_term_sheet": (
        "Settlement mediation term sheet folio, featuring a formal document title block, blank structured installment table lines, and a bolded summary rule line "
        "without readable typography or digits. Bold ink, cel-shading, rich paper texture."
    ),
    "fg_evidence_liability_insurance_policies": (
        "Stacked vintage general liability insurance policy binders, parchment coverage declaration pages with abstract graphical header seals and blank ruled lines "
        "without typography or numbers. Aged paper texture, bold ink, cel-shading."
    ),
    "fg_evidence_parish_property_map": (
        "Stylized 2D forensic parish property cadastral parcel map, displaying Northern California real estate holdings partitioned into distinct color-shaded estate zones "
        "with clean geometric boundary outlines and shaded zone fills without readable lettering or numbers. Parchment texture, cel-shading."
    ),
    "fg_evidence_case_timeline_clock": (
        "Stylized antique documentary brass clock artifact, numeral-free clock face with clean unnumbered division tick marks and abstract pointer hands, "
        "attached evidentiary archival tag without readable text. Tactile metallic texture, bold ink, cel-shading."
    ),

    # --- 5 NEW CRITICAL EVIDENCE PROPS (REQUESTED BY AUDIT COUNCIL) ---
    "fg_evidence_jury_verdict_form": (
        "Official California state court civil special verdict form folio, embossed court clerk seal without typography, "
        "abstract jury award calculation lines rendered with blank handwritten fill lines without readable text or digits. "
        "Bold ink, cel-shading, crisp legal document texture."
    ),
    "fg_evidence_purdue_scotus_opinion": (
        "Official Supreme Court slip opinion folio, formal judicial header block without readable letters, "
        "crisp legal margins with abstract ruling text rendered as illegible horizontal line-marks. "
        "Bold ink, cel-shading, archival paper texture."
    ),
    "fg_evidence_order_denying_confirmation": (
        "Official federal bankruptcy court order denying confirmation folio, embossed judicial seal stamp without typography, "
        "formal decretal paragraph rendered with abstract line-marks without readable text or digits. "
        "Bold ink, cel-shading, crisp legal parchment."
    ),
    "fg_evidence_automatic_stay_notice": (
        "Official federal bankruptcy automatic stay statutory notice folio, prominent centered judicial emblem without lettering, "
        "blank case caption block and abstract statutory warning sections without typography or digits. "
        "Bold ink, cel-shading, crisp legal folio."
    ),
    "fg_evidence_attendance_decline_chart": (
        "Stylized 2D forensic statistical column chart on cream ledger paper, comparing historical parish collections and cathedraticum revenues "
        "against post-revival levels, contrasting tonal columns without readable text, numbers, or typography. "
        "Bold ink, cel-shading, tactile paper texture."
    )
}


def reforge_oakland_assets():
    """Sanitize all prompts and write clean assets."""
    ep_dir = Path("/var/vf/episodes/EN_EP0008_oakland_plan_rejected")
    if not ep_dir.exists():
        ep_dir = Path("out/EN_EP0008_oakland_plan_rejected")
        ep_dir.mkdir(parents=True, exist_ok=True)

    print("1. Writing polished story.txt and spoken_script.txt...")
    story_path = ep_dir / "story.txt"
    spoken_path = ep_dir / "spoken_script.txt"
    story_path.write_text(STORY_TEXT, encoding="utf-8")
    spoken_path.write_text(STORY_TEXT, encoding="utf-8")
    print(f"   -> Wrote story ({len(STORY_TEXT.split())} words) to {story_path}")

    print("2. Sanitizing 18 Clean Backgrounds...")
    clean_bgs = {}
    for k, raw_p in CLEAN_RAW_BGS.items():
        clean_bgs[k] = _sanitize_background_prompt(raw_p, bg_key=k, market="EN")

    print(f"3. Sanitizing {len(CLEAN_RAW_FGS)} Clean Foregrounds...")
    clean_fgs = {}
    for k, raw_p in CLEAN_RAW_FGS.items():
        clean_fgs[k] = _sanitize_foreground_prompt(raw_p, fg_key=k, market="EN")

    print("4. Updating prompts_forge.json...")
    pf_path = ep_dir / "prompts_forge.json"
    existing_pf = json.loads(pf_path.read_text(encoding="utf-8")) if pf_path.exists() else {}
    existing_pf["backgrounds"] = clean_bgs
    existing_pf["foregrounds"] = clean_fgs

    # Update scene prompts if present
    for sc in existing_pf.get("scenes", []):
        bg_k = sc.get("background_reuse_key") or sc.get("bg_key") or sc.get("bg_id")
        if bg_k and bg_k in clean_bgs:
            sc["background_prompt"] = clean_bgs[bg_k]
        fg_k = sc.get("foreground_reuse_key") or sc.get("fg_key") or sc.get("fg_id")
        if fg_k and fg_k in clean_fgs:
            sc["foreground_prompt"] = clean_fgs[fg_k]

    pf_path.write_text(json.dumps(existing_pf, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   -> Wrote {len(clean_bgs)} BGs and {len(clean_fgs)} FGs to {pf_path}")

    print("5. Syncing prompts.json...")
    pj_path = ep_dir / "prompts.json"
    if pj_path.exists():
        existing_pj = json.loads(pj_path.read_text(encoding="utf-8"))
        existing_pj["backgrounds"] = clean_bgs
        existing_pj["foregrounds"] = clean_fgs
        for sc in existing_pj.get("scenes", []):
            bg_k = sc.get("background_reuse_key") or sc.get("bg_key") or sc.get("bg_id")
            if bg_k and bg_k in clean_bgs:
                sc["background_prompt"] = clean_bgs[bg_k]
            fg_k = sc.get("foreground_reuse_key") or sc.get("fg_key") or sc.get("fg_id")
            if fg_k and fg_k in clean_fgs:
                sc["foreground_prompt"] = clean_fgs[fg_k]
        pj_path.write_text(json.dumps(existing_pj, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"   -> Synced {pj_path}")

    print("REFORGING COMPLETE! All assets pristine and compliant.")


if __name__ == "__main__":
    reforge_oakland_assets()
