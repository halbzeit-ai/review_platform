
## Product Requirements Document (PRD)

### KIIS (Key Investor Information Sheet) Module

**For: Crowdfunding Platform (Health Startups, Germany)**

### Goal

- Implement a KIIS generator to comply with German legal requirements (primarily § 13 VermAnlG and EU regulation 2017/1129 for securities if relevant) for each investment offering.
- This KIIS is a view that the startup can see in their project management area.
- The idea is to give the startup the vision of how it will be when they are presented to potential investors. 
- This KIIS is not directly editable by the startup, but they can add information and documents into have the platform fill it for them
(- This KIIS will be displayed to potential investors once they open up a project from the investor's gallery view.)
- when planning this feature, look at the right most column and suggest datasources that either GPs or startups can provide for our AI to analyse and extract relevant data to fill that field.
- obviously, the displayed KIIS will show the data source to the startup but not to the investor, i.e. what a user sees depends on their role

### 1. Required Data Fields and Data Sources

| Field (German legal reference) | Description | Typical Data Source(s) |
| :-- | :-- | :-- |
| Name of the Issuer | Legal name of the startup | Startup registration docs; onboarding form |
| Responsible persons (issuer contact) | Names \& contacts of management/legal reps | Startup onboarding; founder profiles |
| Type of Investment/Product description | What is offered (shares/bonds/loans etc.) + detailed explanation | Startup submission; legal docs |
| Purpose of Fundraising | What the funds will be used for | Startup business plan; onboarding |
| Key Risks | Top 3-5 risk factors for investors | Startup-provided; platform compliance review |
| Investment Amount/Min. Subscription | Total offered, individual min/max investment | Campaign setup form; startup input |
| Duration/Term | Duration for which funds will be locked in or the investment term | Startup legal docs; onboarding |
| Interest/Return Details | Promised returns, dividends, interest; calculation example | Financial plan; term sheet |
| Repayment Schedule | Timetable/plan for disbursements or repayments | Startup legal docs; structured input |
| Fees/Charges | All fees to investors (by platform or issuer) | Platform config; legal docs |
| Exit Scenarios | Under what circumstances can investors exit/redeem investment | Startup legal docs |
| Legal Structure/Prospectus (if needed) | Existence of full prospectus (§ 17 VermAnlG if over €2.5M), legal structure | Uploaded docs by startup |
| Historical Performance | Where relevant, performance data or at least "startup/no track record" statement | Startup-provided; financial statements |
| Conflicts of Interest Disclosure | Any potential conflicts declared | Issuer compliance check; self-disclosure |
| Investor Warnings | Standardized warnings as prescribed by law | Preset platform text (statutory wording) |

### 2. Implementation Guidance

- **Mandatory/Optional Checks:** Implement logic to require data where legally prescribed.
- **Data Collection:** Most data comes from the startup during onboarding, with supplementary checks by platform compliance/legal.
- **Standardized Warnings:** Use statutory text blocks for investor warnings and risk disclosures.
- **Document Generation:** All fields must be assembled and presented in a KIIS PDF or digital doc per campaign.


### 3. Notes

- KIIS must be easily exportable as PDF and viewable before investment commitment.
- Source verification/validation workflows may be required for legal documents.
- Where relevant, fields should include citations to originating source (upload, structured input, preset).

This PRD covers all obligatory KIIS data points and typical sourcing requirements to ensure legal compliance and ease of software implementation for your German health crowdfunding platform.

