# Skill brief: weekly-sales-report

- **Job:** builds the weekly sales report from the CRM export.
- **Kind:** fragile
- **Should load it:** "make this week's sales report", "the CRM export is in Downloads, do the Monday numbers", "zrób raport sprzedaży za ten tydzień"
- **Near misses:** "analyze churn in this CSV" (general analysis, no skill); "update the sales dashboard in Metabase" (`metabase-edit`)
- **Baseline:** a fresh agent summed `amount` including refunds, used the export's UTC timestamps instead of Europe/Warsaw week boundaries, and invented its own table layout.
- **Local facts:** export file is `crm_export_*.csv`, semicolon-separated, decimal comma; refunds have `type=refund` and negative `amount`; weeks run Monday 00:00 to Sunday 23:59 Europe/Warsaw; the report goes to `reports/YYYY-Www.md` using the fixed table in the old reports.
- **Uses other skills:** none
- **Side effects:** none
- **Placement:** project
- **Open questions:** none
