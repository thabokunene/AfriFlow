# 04 Entity Resolution

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

## The Core Challenge

We must match the same corporate client across five
different systems that each have their own client ID,
their own spelling of the company name, and their own
data model.

System | How They Record "Dangote Industries"
--- | ---
CIB | CIB-4521 "Dangote Industries Ltd"
Forex | FX-DANG-NG "Dangote Industries PLC"
Insurance | LIB-POL-88234 "DANGOTE IND."
Cell | MTN-CORP-7891 "Dangote Group"
PBB | PBB-ACC-33445566 "Dangote Ind Limited"

text


We must create ONE universal Golden ID that links all
five records.

## Matching Hierarchy

We apply matching in four phases, ordered by
confidence.

### Phase 1: Registration Number Match (100% confidence)

If two entities share the same company registration
number (e.g., South African CIPC number, Nigerian CAC
number), we match them deterministically. This is the
highest confidence match.

### Phase 2: Tax Number Match (98% confidence)

If entities share the same tax identification number
(e.g., South African tax reference, Nigerian TIN), we
match them. Slightly lower confidence because tax
numbers occasionally contain transcription errors.

### Phase 3: Name Plus Country Match (70 to 90% confidence)

We apply multi step name normalisation and then match
entities that share the same normalised name within the
same country.

Our normalisation steps include removing legal entity
suffixes (Pty Ltd, Limited, PLC, SA, Inc, GmbH, AG),
removing punctuation and special characters,
collapsing whitespace, converting to uppercase, and
handling multilingual variants.

### Phase 4: Contact Detail Match (85% confidence)

We match entities that share verified email domains or
phone number patterns when other methods produce no
match.

## Multilingual Normalisation

This is critical for Africa. We handle name variants
across English, French, Portuguese, and Arabic.

Original | Normalised
--- | ---
SOCIETE NATIONALE D'ELECTRICITE | SOCIETE NATIONALE DELECTRICITE
Société Nationale d'Électricité | SOCIETE NATIONALE DELECTRICITE
SNEL | SNEL (acronym, separate lookup)
Companhia de Electricidade | COMPANHIA DE ELECTRICIDADE

text


We maintain an acronym registry that maps common
corporate acronyms to their full normalised names.
This registry is country specific and manually curated.

## Subsidiary Linking

We go beyond flat record matching. We build a corporate
hierarchy graph that links parent entities to
subsidiaries using typed relationships.

Dangote Industries (GLD-A1B2C3D4E5F6)
├── owns (100%) -> Dangote Cement Nigeria
├── owns (100%) -> Dangote Cement Zambia
├── owns (65%) -> Dangote Sugar Refinery
└── owns (51%) -> Dangote Cement South Africa

text


When we detect a risk signal on a subsidiary, we
propagate it to the parent entity and to all other
subsidiaries in the group. When we calculate total
relationship value, we aggregate across the full
hierarchy.

## Human Verification Queue

We do not trust automated matching below 90%
confidence. For matches in the 60 to 89% range, we
route them to a human verification queue.

The queue presents the RM or data steward with both
entities side by side and asks them to confirm or
reject the match. Confirmed matches train the
probabilistic model over time. Rejected matches are
added to a blocklist to prevent recurrence.

We track verification queue metrics as part of our
data quality framework.

Metric | Target
--- | ---
Matches above 90% confidence | 70%+
Matches requiring verification | 20 to 30%
False match rate (post review) | Below 2%
Queue processing time | Under 48 hours

text


## Golden ID Generation

We generate deterministic Golden IDs using SHA256
hashing of the most stable available identifier
(registration number first, tax number second,
normalised name plus country last).

Golden IDs are prefixed with "GLD-" followed by 12
uppercase hexadecimal characters.

This deterministic approach means that the same input
always produces the same Golden ID, enabling
reproducibility and auditability.

## Known Limitations

We are transparent about the limitations of our entity
resolution approach.

1. **Acronym resolution** requires manual curation. We
   cannot automatically determine that "SNEL" maps to
   "Societe Nationale d'Electricite" without a
   maintained registry.

2. **Cross country subsidiaries** with completely
different names (a South African parent named
"Stellar Mining Holdings" owning a Zambian
subsidiary named "Copperbelt Extraction Ltd") will
not match on name alone. We rely on registration
or tax linkages for these cases.

3. **Simulated data** demonstrates the pipeline logic
   but does not validate match accuracy on real world
   name variations. We explicitly state that accuracy
   metrics from simulated data reflect the simulator
   logic, not production performance.

4. **French and Portuguese name handling** is
   functional but not comprehensive. A production
deployment would require linguist review of the
normalisation rules for Francophone and Lusophone
markets.
