# Corpus

Public insurance documents used by this project. The PDFs themselves live in `data/raw/`
(git-ignored). Re-download them from the URLs below using the file name in the `id` column.

Selected 2026-10-08. Two product lines: **motor** and **travel**. 8 insurers, 2 regulators or
industry bodies, 14 files, **566 pages**.

## Policy wordings: motor

| id | Insurer | Document as printed | Pages | Version / date | Source URL | Why kept |
|---|---|---|---|---|---|---|
| `saga-motor-2025` | Saga (underwritten by Ageas) | Saga Car Insurance Policy Book | 88 | SAGACARPB DEC 25 | https://www.saga.co.uk/helix-contentlibrary/saga/insurance/pdfs/car/saga-car-insurance-policy-book-december-2025.pdf?cd=download | Richest motor document: Standard / Select / Plus comparison tables with limits, worked excess examples (young-driver excess), definitions, many optional covers, endorsements |
| `directline-motor-2025` | Direct Line | Your Car Insurance Policy Booklet | 48 | B4C DL M PB 1225 (Dec 2025) | https://assets.directline.com/motor-docs/policy-booklet-1225.pdf | Clean four-tier "what your cover includes" tables (TPFT / Essentials / Comprehensive / Comprehensive Plus); glossary instead of a "Definitions" heading; optional extras |
| `tesco-motor-2026` | Tesco Insurance | Tesco Car Insurance Cover Policy Booklet | 54 | 0226 (Feb 2026) | https://tesco-ims-insurance-prod-endpoint-e8g3g4a6f0b4cndy.a03.azurefd.net/media-17119564-7ad9-4407-aae7-ea82475d0b0c/74baf863-99c8-4b3c-be03-ee8217b65186/tesco-car-insurance-cover-policy-booklet-0226.pdf | Explicit "Table of features and limits" across five products (Bronze / Silver / Gold comprehensive, Silver TPFT, Silver TPO) plus an additional-cover table; definitions; endorsements. CDN URL may rotate; stable entry point is https://www.tescoinsurance.com/car-insurance/ |
| `axa-motor-2023` | AXA | AXA Car Insurance - Your policy wording | 56 | ACPD0392P-C (03/23) | https://www.axa.co.uk/globalassets/pdfs/motor/april-2023/axa-direct-car-policy-wording-acpd0392p-c.pdf/ | Most formal legal structure: long Definitions section, many exclusion clauses, personal-injury benefit table, breakdown sections. Good style contrast |
| `aviva-motor-2026` | Aviva | Aviva Signature motor insurance policy | 38 | NMDMG10249 04.2026 | https://static.aviva.io/content/dam/aviva-public/gb/pdfs/personal/insurance/motor/car/insurance-motor-car-policy-wording-document-NMDMG10249.pdf | Definitions; optional sections (Motor Legal, Motor Injury Protection Plus, Foreign use). Excess amounts are in the companion sheet below |
| `aviva-motor-limits-2026` | Aviva | Motor cover limits (companion sheet to the Aviva policy) | 5 | NMDMG15456 06.2026 | https://static.aviva.io/content/dam/aviva-public/gb/pdfs/personal/insurance/motor/car/aviva-motor-cover-limits-NMDMG15456.pdf | The only true numeric excess table in the motor set: windscreen replacement and repair excesses, policy excess and non-approved-repairer excess by cover level. Treat as part of the Aviva motor product |

## Policy wordings: travel

| id | Insurer | Document as printed | Pages | Version / date | Source URL | Why kept |
|---|---|---|---|---|---|---|
| `staysure-travel-2026` | Staysure | Travel insurance policy July 2026 (Basic / Comprehensive / Signature) | 56 | V21, valid from 28 Jul 2026 | https://cms-public.staysure.co.uk/dam/jcr:bcd870a5-ec6a-4817-bd96-f6ae82e13b52/PW_Staysure_Sig_0726%20V21%20WEB.pdf | Best all-rounder: table of benefits with limits per tier and an excess column; "Pre-existing medical conditions" section; "Definitions" section; optional covers (winter sports, cruise, gadget, golf, excess waiver); per-section "Claims evidence" lists |
| `postoffice-travel-2026` | Post Office | Your Travel Insurance Policy (Economy / Standard / Premier) | 33 | PL10244, March 2026 | https://www.postoffice.co.uk/dam6/jcr:17bfed70-9c2b-411c-ae43-194795af77d7/direct_policy_wording_2603.2026-03-09-11-20-50.pdf | Table of benefits with both limit and excess per section for three tiers; "General Definitions"; optional extras incl. gadget and cruise. **Hard formatting:** each PDF page is a two-page printed spread, so one PDF page holds two printed pages. Uses "existing medical condition" rather than "pre-existing" |
| `saga-travel-2025` | Saga | Your Policy Book - Standard and Plus Travel Insurance | 44 | TR3320, Nov/Dec 2025 | https://www.saga.co.uk/helix-contentlibrary/saga/insurance/pdfs/travel/saga-standard-and-plus-travel-policy-book-101225.pdf?cd=download | Two "summary of cover - limits and excesses" tables (one per tier); Definitions; medical declaration; winter sports and cruise sections. Same insurer as `saga-motor-2025`, which tests product-line filtering |
| `churchill-travel-2024` | Churchill (UK Insurance Ltd) | Your travel insurance policy booklet | 40 | PB 0624 (June 2024) | https://www.churchill.com/assets/pdf/ch-travel-policy-document.pdf | Definitions section; pre-existing conditions discussed throughout; limits and excesses given as a box at the start of each section rather than one table; five optional sections (ski equipment, ski pack, piste closure, golf, wedding). Uses "personal possessions" instead of "baggage", which tests synonym retrieval |

## Regulator and industry-body guidance

| id | Publisher | Document as printed | Pages | Date | Source URL | Why kept |
|---|---|---|---|---|---|---|
| `fca-motor-claims-2025` | Financial Conduct Authority (UK) | Motor Insurance Claims Analysis, multi-firm review | 33 | July 2025 | https://www.fca.org.uk/publication/multi-firm-reviews/motor-insurance-claims-analysis-multi-firm-review-2025.pdf | Current regulator view on motor claims handling, total-loss valuations and repair delays. Plain narrative with charts; pairs with the motor wordings for cross-document questions |
| `fca-travel-medical-2024` | Financial Conduct Authority (UK) | Post implementation review of the travel insurance signposting rules for consumers with medical conditions | 37 | April 2024 | https://www.fca.org.uk/publication/multi-firm-reviews/post-implementation-review-travel-insurance-signposting-rules-consumers-medical-conditions-2024.pdf | Travel insurance for people with pre-existing medical conditions; 139 numbered paragraphs, which makes chunk boundaries and citations easy to check |
| `abi-salvage-code-2025` | Association of British Insurers | Code of Practice for the Categorisation of Motorised Vehicle Salvage | 27 | 28 May 2025 | Original: https://www.abi.org.uk/globalassets/files/publications/public/motor/2025/codepracticecategorisationmotorisedvehiclesalvagemay2025.pdf. Mirror that works for scripts: https://web.archive.org/web/20250529143002id_/https://www.abi.org.uk/globalassets/files/publications/public/motor/2025/codepracticecategorisationmotorisedvehiclesalvagemay2025.pdf | Crisp numbered definitions of write-off categories A, B, S and N; produces precise, checkable answers. abi.org.uk returns HTTP 403 to non-browser clients, so use the mirror when scripting |

## Deliberately hard document

| id | Publisher | Document as printed | Pages | Date | Source URL | Why kept |
|---|---|---|---|---|---|---|
| `bajaj-motor-scanned-2013` | Bajaj Allianz General Insurance (India) | Private car policy wording | 7 | Wayback capture 29 Apr 2013 | https://web.archive.org/web/20130429192259id_/http://www.bajajallianz.com/Corp/content/motor/car-Policy-wording.pdf | Image-only scan: pypdf extracts zero characters. Forces the OCR path in the parser. Satisfies the PRD requirement for at least one scanned document |

## Why motor and travel

Motor wordings have the richest **tier comparison tables** (limits per cover level), fixed
**windscreen excesses**, and long **optional cover** sections that override earlier clauses.
Travel wordings have **benefits tables with limits and excesses per section**, strong
**definitions** (especially "pre-existing medical condition"), and **claims evidence** lists that
map directly to the PRD use case "what must be submitted for a claim". Having both Saga and Aviva
appear in more than one document also tests metadata filtering by insurer and product line.

## Known quirks to handle in ingestion

- **Encrypted PDFs.** `tesco-motor-2026`, `axa-motor-2023`, both Aviva motor files and both FCA
  files are AES-encrypted with an empty user password (they open normally in a viewer). pypdf
  needs the `cryptography` package to read them. Docling's default backend handles them.
- **Two-page spreads.** `postoffice-travel-2026` has two printed pages per PDF page. Citations
  will use the PDF page index, not the printed page number.
- **Image-only scan.** `bajaj-motor-scanned-2013` has no text layer and needs OCR.
- **Unstable URL.** The Tesco CDN URL contains GUIDs and may change; the stable entry point is
  the Tesco car insurance page.
- **Excess amounts.** UK motor booklets do not print the customer's own compulsory or voluntary
  excess; they say "shown on your schedule". Fixed windscreen excesses and cover-limit tables are
  what the golden set should target.

## Verified but not selected (candidates for later or for a de-duplication test)

Motor: AXA Plus (ACPD0393P-C), Ageas Sep 2025 and Ageas Essentials, esure Core and Flex (Sep 2025),
Admiral AD-003-040, Saga Select/Plus and Standard (Dec 2023).
Travel: AXA Travel V3 (2026), Aviva Signature Travel NTRTG10145 (2026), Direct Line travel PB 0624
(near-duplicate of Churchill, same underwriter).
Regulator: FCA TR24/2 (fair value), FCA TR19/2, EIOPA Consumer Trends Report 2024, Central Bank of
Ireland Insurance Regulations 2022 Q&A, ABI codes on third-party assistance, misrepresentation and
telematics.
Hard documents: New India Assurance CPA wording (text layer exists but is garbage OCR), Aviva
Private Clients motor 2016 (words split mid-line), AAA "Protector" 1981 scanned brochure.
